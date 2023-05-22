import asyncio
import json
import os
import platform
from typing import Callable, Optional

import aiohttp
from pydantic import BaseModel
from roster_agent_runtime.controllers.agent import errors
from roster_agent_runtime.executors.base import AgentExecutor
from roster_agent_runtime.listeners.base import EventListener
from roster_agent_runtime.listeners.docker import (
    DEFAULT_EVENT_FILTERS,
    DockerEventListener,
)
from roster_agent_runtime.models.agent import (
    AgentCapabilities,
    AgentContainer,
    AgentSpec,
    AgentStatus,
)
from roster_agent_runtime.models.conversation import ConversationMessage
from roster_agent_runtime.models.task import TaskSpec, TaskStatus

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


class RunningAgent(BaseModel):
    status: AgentStatus
    tasks: dict[str, TaskStatus] = {}


# TODO: lots of methods probably need to be transactional
# TODO: make docker client operations async
class DockerAgentExecutor(AgentExecutor):
    ROSTER_CONTAINER_LABEL = "roster-agent"
    task_informer_middleware = [parse_task_status_line]

    def __init__(self):
        try:
            self.client = docker.from_env()
            self.agents: dict[str, RunningAgent] = {}
            # This is for convenient access without an agent name
            self.tasks: dict[str, TaskStatus] = {}

            # This informer allows us to listen for changes to
            # container status in the Docker environment.
            self.docker_events_informer = DockerEventListener(
                filters={"label": self.ROSTER_CONTAINER_LABEL, **DEFAULT_EVENT_FILTERS},
                handlers=[self._handle_docker_event],
            )
            # TODO: cleaner task management
            self.docker_events_informer.run_as_task()

            # These informers allow us to listen for changes to
            # task status within an Agent container.
            self.task_listeners: dict[str, EventListener] = {}

            # These listeners allow us to notify the agent service
            # of changes to agent and task status.
            self.agent_status_listeners: list[Callable] = []
            self.task_status_listeners: list[Callable] = []
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

    async def _restore_agent_state(self):
        containers = self.client.containers.list(
            filters={"label": self.ROSTER_CONTAINER_LABEL}
        )
        for container in containers:
            self._add_agent_from_container(container)

    async def _fetch_task_status_for_agent(self, agent_name: str) -> list[TaskStatus]:
        # Using mock data to test:
        return [TaskStatus(agent_name=agent_name, name="MyTask", status="running")]
        # try:
        #     url = (
        #         f"http://localhost:{self._get_service_port_for_agent(agent_name)}/tasks"
        #     )
        #     async with aiohttp.ClientSession() as session:
        #         async with session.get(url) as response:
        #             assert response.status == 200
        #             return [
        #                 TaskStatus(**task_status)
        #                 for task_status in await response.json()
        #             ]
        # except AssertionError as e:
        #     raise errors.AgentServiceError(
        #         f"Could not fetch task status from agent {agent_name}."
        #     ) from e
        # except (TypeError, KeyError, aiohttp.ContentTypeError) as e:
        #     raise errors.AgentServiceError(
        #         f"Could not parse response from agent {agent_name}."
        #     ) from e
        # except (aiohttp.ClientError, errors.AgentServiceError):
        #     # This can happen if the agent is not yet ready to respond to requests.
        #     return []

    async def _restore_task_state(self):
        agent_names = list(self.agents.keys())
        task_status_lists = await asyncio.gather(
            *[
                self._fetch_task_status_for_agent(agent_name)
                for agent_name in agent_names
            ]
        )
        for agent_name, task_status_list in zip(agent_names, task_status_lists):
            for task_status in task_status_list:
                self._store_task(agent_name, task_status)

    async def setup(self):
        await asyncio.gather(self._restore_agent_state(), self._restore_task_state())

    def list_agents(self) -> list[AgentStatus]:
        return [agent.status for agent in self.agents.values()]

    def get_agent(self, name: str) -> AgentStatus:
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

        self._add_agent_from_container(container)
        return self.agents[agent.name].status

    async def update_agent(self, agent: AgentSpec) -> AgentStatus:
        # NOTE: delete then recreate strategy is used for simplicity
        #   but will kill all running tasks
        try:
            await self.delete_agent(agent.name)
        except errors.AgentServiceError:
            raise errors.AgentServiceError(f"Could not update agent {agent.name}.")

        return await self.create_agent(agent)

    async def delete_agent(self, name: str) -> None:
        try:
            running_agent = self.agents.pop(name)
            for task in running_agent.tasks.values():
                self.tasks.pop(task.name, None)
        except KeyError:
            raise errors.AgentNotFoundError(agent=name)

        try:
            self.task_listeners.pop(name).cancel()
        except (KeyError, RuntimeError):
            # NOTE: informer was not started
            #   should log warning here
            pass

        if not running_agent.status.container:
            raise errors.AgentNotFoundError(agent=name)

        try:
            container = self.client.containers.get(running_agent.status.container.id)
        except docker.errors.NotFound:
            raise errors.AgentNotFoundError(agent=name)

        try:
            container.stop()
            container.remove()
        except docker.errors.APIError as e:
            raise errors.AgentServiceError(f"Could not delete agent {name}.") from e

    def _task_event_handler(self, agent_name: str) -> Callable:
        def handler(task: TaskStatus) -> None:
            try:
                self._store_task(agent_name, task)
                for listener in self.task_status_listeners:
                    listener(task)
            except KeyError:
                # should probably just log an error instead of breaking
                # the informer
                raise errors.AgentNotFoundError(agent=agent_name)
            except Exception:
                # this is likely a listener error
                # should probably log an error here
                pass

        return handler

    def _store_task(self, agent_name: str, task: TaskStatus):
        self.agents[agent_name].tasks[task.name] = task
        self.tasks[task.name] = task

    async def initiate_task(self, task: TaskSpec) -> TaskStatus:
        port = self._get_service_port_for_agent(task.agent_name)
        url = f"http://localhost:{port}/task"

        payload = {"name": task.name, "description": task.description}

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    url, json=payload, raise_for_status=True
                ) as response:
                    try:
                        response = await response.json()
                        task_status = TaskStatus(**response)
                        self._store_task(task.agent_name, task_status)
                    except (TypeError, aiohttp.ContentTypeError) as e:
                        raise errors.AgentServiceError(
                            f"Could not parse response from agent {task.agent_name}."
                        ) from e
            except aiohttp.ClientError as e:
                raise errors.AgentServiceError(
                    f"Could not initiate task {task.name}."
                ) from e

        if task.agent_name not in self.task_listeners:
            # TODO: figure out how to wait for agent server to be ready
            #   and start this instead from create_agent
            #   - this is essentially lazy loading (so maybe keep it?)
            self.task_listeners[task.agent_name] = EventListener(
                url=f"http://localhost:{port}/task_events",
                middleware=self.task_informer_middleware,
                handlers=[self._task_event_handler(task.agent_name)],
            )
            self.task_listeners[task.agent_name].run_as_task()

        return task_status

    async def update_task(self, task: TaskSpec) -> TaskStatus:
        try:
            await self.end_task(task.name)
        except errors.TaskNotFoundError:
            raise errors.TaskNotFoundError(task=task.name)

        return await self.initiate_task(task)

    def list_tasks(self) -> list[TaskStatus]:
        return list(self.tasks.values())

    def get_task(self, task: TaskSpec) -> TaskStatus:
        try:
            return self.tasks[task.name]
        except KeyError:
            raise errors.TaskNotFoundError(task=task.name)

    async def end_task(self, name: str) -> None:
        task = self.tasks.get(name)
        if not task:
            raise errors.TaskNotFoundError(task=name)
        port = self._get_service_port_for_agent(task.agent_name)
        url = f"http://localhost:{port}/task"

        payload = {"name": task.name}

        async with aiohttp.ClientSession() as session:
            try:
                async with session.delete(
                    url, json=payload, raise_for_status=True
                ) as response:
                    assert response.status == 204
            except (AssertionError, aiohttp.ClientError) as e:
                raise errors.AgentServiceError(
                    f"Could not end task {task.name}."
                ) from e

    async def prompt(
        self,
        name: str,
        history: list[ConversationMessage],
        message: ConversationMessage,
    ) -> ConversationMessage:
        complete_chat = [message, *history]
        port = self._get_service_port_for_agent(name)
        url = f"http://localhost:{port}/chat"

        payload = [message.dict() for message in complete_chat]

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
                            f"Could not parse response from agent {name}."
                        ) from e
            except aiohttp.ClientError as e:
                raise errors.AgentServiceError(
                    f"Could not connect to agent {name}."
                ) from e

        return conversation_message

    def _find_agent_by_container_name(
        self, container_name: str
    ) -> Optional[RunningAgent]:
        for agent in self.agents.values():
            if (
                agent.status.container is not None
                and agent.status.container.name == container_name
            ):
                return agent

    async def _handle_docker_event(self, event: dict):
        if event["Type"] != "container":
            return

        if event["Action"] not in ["start", "stop", "die", "destroy"]:
            return

        try:
            container_name = event["Actor"]["Attributes"]["name"]
            agent = self._find_agent_by_container_name(container_name)
            container = self.client.containers.get(container_name)
        except (KeyError, docker.errors.NotFound):
            return

        if agent is None:
            return

        agent.status.container = serialize_agent_container(container)
        agent.status.status = container.status

        for listener in self.agent_status_listeners:
            listener(agent.status)

    def add_agent_status_listener(self, listener: Callable):
        self.agent_status_listeners.append(listener)

    def add_task_status_listener(self, listener: Callable):
        self.task_status_listeners.append(listener)
