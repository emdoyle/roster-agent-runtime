import asyncio
import json
import os
import platform
from typing import Callable

import aiohttp
from pydantic import BaseModel
from roster_agent_runtime.executors.base import AgentExecutor
from roster_agent_runtime.informers.base import Informer
from roster_agent_runtime.models.agent import (
    AgentCapabilities,
    AgentContainer,
    AgentSpec,
    AgentStatus,
)
from roster_agent_runtime.models.conversation import (
    ConversationMessage,
    ConversationResource,
)
from roster_agent_runtime.models.task import TaskSpec, TaskStatus
from roster_agent_runtime.services.agent import errors

import docker


def get_host_ip(network_name="bridge", client=None):
    os_name = platform.system()

    if os_name == "Linux":
        client = client or docker.from_env()
        network = client.networks.get(network_name)
        try:
            gateway = network.attrs["IPAM"]["Config"][0]["Gateway"]
        except (IndexError, KeyError):
            raise errors.AgentServiceError(
                "Could not determine host IP for network: {}".format(network_name)
            )
        return gateway

    elif os_name == "Darwin" or os_name == "Windows":
        return "host.docker.internal"

    else:
        raise errors.AgentServiceError(
            "Unsupported operating system: {}".format(os_name)
        )


def serialize_agent_container(
    container: "docker.models.containers.Container",
) -> AgentContainer:
    capabilities = AgentCapabilities(
        network_access=container.attrs["HostConfig"]["NetworkMode"] == "default",
        messaging_access=container.labels.get("messaging_access", False) == "True",
    )
    return AgentContainer(
        id=container.id,
        name=container.name,
        image=container.image.tags[0],
        status=container.status,
        labels=container.labels,
        capabilities=capabilities,
    )


def parse_task_status_line(line: str) -> TaskStatus:
    try:
        task_status = TaskStatus(**json.loads(line))
    except (TypeError, json.JSONDecodeError) as e:
        raise errors.AgentServiceError(
            "Could not parse task status line from agent."
        ) from e
    return task_status


task_informer_middleware = [parse_task_status_line]


class RunningAgent(BaseModel):
    status: AgentStatus
    tasks: dict[str, TaskStatus] = {}


# TODO: make docker client operations async
class DockerAgentExecutor(AgentExecutor):
    ROSTER_CONTAINER_LABEL = "roster-agent"

    def __init__(self):
        try:
            self.client = docker.from_env()
            self.agents: dict[str, RunningAgent] = {}
            self.informers: dict[str, Informer] = {}
            self.restore_state()
        except docker.errors.DockerException as e:
            raise errors.AgentServiceError("Could not connect to Docker daemon.") from e

    @property
    def host_ip(self):
        return get_host_ip(client=self.client)

    def _labels_for_agent(self, agent: AgentSpec) -> dict:
        return {
            self.ROSTER_CONTAINER_LABEL: agent.name,
            "messaging_access": str(agent.capabilities.messaging_access),
        }

    def _get_service_port_for_agent(self, name: str) -> int:
        running_agent = self.agents.get(name)
        if not running_agent or not running_agent.status.container:
            # TODO: fallback to docker API calls
            #   or don't, if we are reacting to docker events
            raise errors.AgentNotFoundError(agent=name)

        try:
            container = self.client.containers.get(running_agent.status.container.id)
        except docker.errors.NotFound:
            raise errors.AgentNotFoundError(agent=name)

        try:
            return container.attrs["NetworkSettings"]["Ports"]["8000/tcp"][0][
                "HostPort"
            ]
        except (IndexError, KeyError):
            raise errors.AgentServiceError(
                f"Could not determine host port for agent {name}."
            )

    async def _fetch_task_status_for_agent(
        self, agent_name: str, session: aiohttp.ClientSession
    ) -> list[TaskStatus]:
        try:
            url = (
                f"http://localhost:{self._get_service_port_for_agent(agent_name)}/tasks"
            )
            async with session.get(url, raise_for_status=True) as response:
                try:
                    response = await response.json()
                    return [
                        TaskStatus(**task_status) for task_status in response["tasks"]
                    ]
                except (TypeError, KeyError, aiohttp.ContentTypeError) as e:
                    raise errors.AgentServiceError(
                        f"Could not parse response from agent {agent_name}."
                    ) from e
        except (aiohttp.ClientError, errors.AgentServiceError):
            return []

    def _add_agent_from_container(
        self, container: "docker.models.containers.Container"
    ):
        agent_container = serialize_agent_container(container)
        try:
            agent_name = container.labels[self.ROSTER_CONTAINER_LABEL]
        except KeyError:
            raise errors.AgentServiceError(
                f"Could not restore agent from container {container.name}."
            )
        self.agents[agent_name] = RunningAgent(
            status=AgentStatus(
                name=agent_name,
                container=agent_container,
                status=agent_container.status,
            ),
            tasks={},
        )

    def _restore_agent_state(self):
        containers = self.client.containers.list(
            filters={"label": self.ROSTER_CONTAINER_LABEL}
        )
        for container in containers:
            self._add_agent_from_container(container)

    def _restore_task_state(self):
        agent_names = list(self.agents.keys())
        loop = asyncio.get_event_loop()
        session = aiohttp.ClientSession()
        try:
            tasks = loop.run_until_complete(
                asyncio.gather(
                    *[
                        self._fetch_task_status_for_agent(name, session)
                        for name in agent_names
                    ]
                )
            )
            for name, task_statuses in zip(agent_names, tasks):
                self.agents[name].tasks.update(
                    {task_status.name: task_status for task_status in task_statuses}
                )
        finally:
            loop.run_until_complete(session.close())

    def restore_state(self):
        self._restore_agent_state()
        self._restore_task_state()

    async def list_agents(self) -> list[AgentStatus]:
        return [agent.status for agent in self.agents.values()]

    async def get_agent(self, name: str) -> AgentStatus:
        try:
            return self.agents[name].status
        except KeyError:
            raise errors.AgentNotFoundError(agent=name)

    async def create_agent(self, agent: AgentSpec) -> AgentStatus:
        if agent.name in self.agents:
            raise errors.AgentAlreadyExistsError(agent=agent.name)

        try:
            if not self.client.images.list(name=agent.image):
                self.client.images.pull(agent.image)
        except docker.errors.ImageNotFound as e:
            raise errors.AgentImageNotFoundError(image=agent.image) from e
        except docker.errors.APIError as e:
            raise errors.AgentServiceError("Could not pull image.") from e

        if agent.capabilities.network_access:
            network_mode = "default"
        else:
            network_mode = None

        try:
            container = self.client.containers.run(
                agent.image,
                detach=True,
                labels=self._labels_for_agent(agent),
                # TODO: figure out user-defined network to allow specific service access only
                network_mode=network_mode,
                ports={"8000/tcp": None},
                environment={
                    "ROSTER_RUNTIME_IP": self.host_ip,
                    "ROSTER_AGENT_NAME": agent.name,
                    "ROSTER_AGENT_PORT": "8000",
                    # TODO: figure out non-roster environment variables
                    "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
                },
            )
            container.reload()
        except docker.errors.APIError as e:
            raise errors.AgentServiceError(
                f"Could not create agent {agent.name}."
            ) from e

        # TODO: figure out how to wait for agent server to be ready

        self.agents[agent.name] = self._add_agent_from_container(container)
        return self.agents[agent.name].status

    async def update_agent(self, agent: AgentSpec) -> AgentStatus:
        # NOTE: delete then recreate strategy is used for simplicity
        #   but will kill all running tasks
        try:
            await self.delete_agent(agent)
        except errors.AgentServiceError:
            raise errors.AgentServiceError(f"Could not update agent {agent.name}.")

        return await self.create_agent(agent)

    async def delete_agent(self, agent: AgentSpec) -> None:
        try:
            running_agent = self.agents.pop(agent.name)
        except KeyError:
            raise errors.AgentNotFoundError(agent=agent.name)

        try:
            self.informers.pop(agent.name).cancel()
        except RuntimeError:
            # NOTE: informer was not started
            #   should log warning here
            pass

        if not running_agent.status.container:
            raise errors.AgentNotFoundError(agent=agent.name)

        try:
            container = self.client.containers.get(running_agent.status.container.id)
        except docker.errors.NotFound:
            raise errors.AgentNotFoundError(agent=agent.name)

        try:
            container.stop()
            container.remove()
        except docker.errors.APIError as e:
            raise errors.AgentServiceError(
                f"Could not delete agent {agent.name}."
            ) from e

    def _task_event_handler(self, agent_name: str) -> Callable:
        def handler(task: TaskStatus) -> None:
            try:
                self.agents[agent_name].tasks[task.name] = task
            except KeyError:
                # should probably just log an error instead of breaking
                # the informer
                raise errors.AgentNotFoundError(agent=agent_name)

        return handler

    async def initiate_task(self, task: TaskSpec) -> TaskStatus:
        port = self._get_service_port_for_agent(task.agent_name)
        url = f"http://localhost:{port}/execute_task"

        payload = {"name": task.name, "description": task.description}

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    url, json=payload, raise_for_status=True
                ) as response:
                    try:
                        response = await response.json()
                        task_status = TaskStatus(**response)
                        self.agents[task.agent_name].tasks[task.name] = task_status
                    except (TypeError, aiohttp.ContentTypeError) as e:
                        raise errors.AgentServiceError(
                            f"Could not parse response from agent {task.agent_name}."
                        ) from e
            except aiohttp.ClientError as e:
                raise errors.AgentServiceError(
                    f"Could not initiate task {task.name}."
                ) from e

        if task.agent_name not in self.informers:
            self.informers[task.agent_name] = Informer(
                url=f"http://localhost:{port}/task_events",
                middleware=task_informer_middleware,
                handlers=[self._task_event_handler(task.agent_name)],
            )
            self.informers[task.agent_name].run_as_task()

        return task_status

    async def prompt(
        self,
        conversation: ConversationResource,
        conversation_message: ConversationMessage,
    ) -> ConversationMessage:
        agent_name = conversation.spec.agent_name
        history = conversation.status.history
        history.append(conversation_message)
        port = self._get_service_port_for_agent(agent_name)
        url = f"http://localhost:{port}/chat"

        payload = [message.dict() for message in history]

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    url, json=payload, raise_for_status=True
                ) as response:
                    try:
                        response = await response.json()
                        conversation_message = ConversationMessage(**response)
                    except (TypeError, aiohttp.ContentTypeError) as e:
                        raise errors.AgentServiceError(
                            f"Could not parse response from agent {agent_name}."
                        ) from e
            except aiohttp.ClientError as e:
                raise errors.AgentServiceError(
                    f"Could not connect to agent {agent_name}."
                ) from e

        return conversation_message
