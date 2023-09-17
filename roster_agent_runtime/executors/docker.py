import asyncio
import os
import platform
from typing import Callable, Optional

import aiohttp
from pydantic import BaseModel, Field
from roster_agent_runtime import errors, settings
from roster_agent_runtime.agents import AgentHandle, HttpAgentHandle
from roster_agent_runtime.executors.base import AgentExecutor
from roster_agent_runtime.executors.events import ResourceStatusEvent
from roster_agent_runtime.executors.store import AgentExecutorStore
from roster_agent_runtime.listeners.docker import (
    DEFAULT_EVENT_FILTERS,
    DockerEventListener,
)
from roster_agent_runtime.logs import app_logger
from roster_agent_runtime.models.agent import AgentContainer, AgentSpec, AgentStatus

import docker

logger = app_logger()


def get_docker_host_ip(network_name="bridge", client=None):
    os_name = platform.system()

    if os_name == "Linux":
        client = client or docker.from_env()
        network = client.networks.get(network_name)
        try:
            gateway = network.attrs["IPAM"]["Config"][0]["Gateway"]
        except (IndexError, KeyError):
            raise errors.RosterError(
                "Could not determine host IP for network: {}".format(network_name)
            )
        return gateway

    elif os_name == "Darwin" or os_name == "Windows":
        return "host.docker.internal"

    else:
        raise errors.RosterError("Unsupported operating system: {}".format(os_name))


def serialize_agent_container(
    container: "docker.models.containers.Container",
) -> AgentContainer:
    return AgentContainer(
        id=container.id,
        name=container.name,
        image=container.image.tags[0] if container.image.tags else "UNKNOWN",
        status=container.status,
        labels=container.labels,
    )


class ExpectedStatusEvent(BaseModel):
    action: str
    agent_name: str
    expiration: float = Field(
        default_factory=lambda: asyncio.get_event_loop().time() + 60
    )

    class Config:
        arbitrary_types_allowed = True

    def __str__(self):
        return f"({self.action} {self.agent_name})"

    @classmethod
    def docker_start(cls, agent_name: str) -> "ExpectedStatusEvent":
        return cls(action="start", agent_name=agent_name)

    @classmethod
    def docker_delete(cls, agent_name: str) -> list["ExpectedStatusEvent"]:
        return [
            cls(action="stop", agent_name=agent_name),
            cls(action="die", agent_name=agent_name),
            cls(action="destroy", agent_name=agent_name),
        ]


# TODO: make docker client operations async
class DockerAgentExecutor(AgentExecutor):
    KEY = "docker"
    ROSTER_CONTAINER_LABEL = "roster-agent"

    def __init__(self):
        try:
            self.client = docker.from_env()

            # Local state: a picture of the Docker environment
            self.store = AgentExecutorStore()

            # This allows us to listen for changes to
            # container status in the Docker environment.
            self.docker_events_listener = DockerEventListener(
                filters={
                    "label": {self.ROSTER_CONTAINER_LABEL: True},
                    **DEFAULT_EVENT_FILTERS,
                },
                handlers=[self._handle_docker_event],
            )

            # These tasks handle the activity stream of each Agent
            # (pushing things like Thoughts, Actions to long-term storage)
            self.activity_stream_tasks: dict[str, asyncio.Task] = {}
            self.roster_activity_url = settings.ROSTER_API_ACTIVITY_URL

            # Synchronization primitives for concurrency control
            self._resource_locks: dict[str, asyncio.Lock] = {}
            self._expected_events: list[ExpectedStatusEvent] = []
        except docker.errors.DockerException as e:
            raise errors.RosterError("Could not connect to Docker daemon.") from e

    @property
    def docker_host_ip(self):
        return get_docker_host_ip(client=self.client)

    def get_agent_lock(self, name: str):
        # NOTE: locks are never cleared, so this will leak memory in the long term
        key = f"agent:{name}"
        if key not in self._resource_locks:
            self._resource_locks[key] = asyncio.Lock()
        return self._resource_locks[key]

    def _push_expected_events(self, *events: ExpectedStatusEvent):
        self._expected_events.extend(events)

    def _pop_expected_event(
        self, agent_name: str, action: str
    ) -> Optional[ExpectedStatusEvent]:
        result = None
        result_idx = None
        for i, expected_event in enumerate(
            filter(
                lambda event: event.expiration > asyncio.get_event_loop().time(),
                self._expected_events,
            )
        ):
            if (
                expected_event.agent_name == agent_name
                and expected_event.action == action
            ):
                result = expected_event
                result_idx = i
                break
        if result and result_idx is not None:
            return self._expected_events.pop(result_idx)
        return None

    def _pop_expected_events(self, *events: ExpectedStatusEvent):
        for event in events:
            self._pop_expected_event(event.agent_name, event.action)

    def _labels_for_agent(self, agent: AgentSpec) -> dict:
        return {
            self.ROSTER_CONTAINER_LABEL: agent.name,
        }

    def _get_service_port_for_agent(self, name: str) -> int:
        agent = self.store.agents.get(name)
        if not agent or not agent.container:
            raise errors.AgentNotFoundError(agent=name)

        try:
            container = self.client.containers.get(agent.container.id)
        except docker.errors.NotFound:
            raise errors.AgentNotFoundError(agent=name)

        try:
            return container.attrs["NetworkSettings"]["Ports"]["8000/tcp"][0][
                "HostPort"
            ]
        except (IndexError, KeyError):
            raise errors.RosterError(f"Could not determine host port for agent {name}.")

    def _add_agent_from_container(
        self, container: "docker.models.containers.Container"
    ) -> AgentStatus:
        agent_container = serialize_agent_container(container)
        try:
            agent_name = container.labels[self.ROSTER_CONTAINER_LABEL]
        except KeyError:
            raise errors.RosterError(
                f"Could not restore agent from container {container.name}."
            )
        agent_status = AgentStatus(
            name=agent_name,
            executor=self.KEY,
            container=agent_container,
            status=agent_container.status,
        )
        self.store.put_agent(agent_status)
        return agent_status

    async def _restore_agent_state(self):
        containers = self.client.containers.list(
            filters={"label": self.ROSTER_CONTAINER_LABEL}
        )
        for container in containers:
            agent_status = self._add_agent_from_container(container)
            if agent_status.name not in self.activity_stream_tasks:
                await self._start_activity_stream_watcher(agent_status.name)

    async def setup(self):
        logger.debug("(docker) Setup started.")
        try:
            logger.debug("(docker) Restoring state...")
            await self._restore_agent_state()
            logger.debug("(docker) State restored.")
            logger.debug("(docker) Starting Docker event listener...")
            self.docker_events_listener.run_as_task()
            logger.debug("(docker) Docker event listener started.")
        except Exception as e:
            await self.teardown()
            raise errors.RosterError("Could not setup Docker executor.") from e
        logger.debug("(docker) Setup complete.")

    async def teardown(self):
        logger.debug("(docker) Teardown started.")
        try:
            self.docker_events_listener.stop()
            for task in self.activity_stream_tasks.values():
                if not task.cancelled():
                    task.cancel()
        except Exception as e:
            raise errors.RosterError("Could not teardown Docker executor.") from e
        logger.debug("(docker) Teardown complete.")

    def list_agents(self) -> list[AgentStatus]:
        return list(self.store.agents.values())

    def get_agent(self, name: str) -> AgentStatus:
        try:
            return self.store.agents[name]
        except KeyError:
            raise errors.AgentNotFoundError(agent=name)

    async def _wait_for_agent_healthy(
        self, agent_name: str, max_retries: int = 40, interval: float = 0.5
    ):
        for i in range(max_retries):
            logger.debug(
                "(agent-exec) %s - Checking agent %s is healthy...", i, agent_name
            )
            try:
                port = self._get_service_port_for_agent(agent_name)
                url = f"http://localhost:{port}/healthcheck"

                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as response:
                        if response.status == 200:
                            return
            except (aiohttp.ClientError, errors.AgentNotFoundError):
                pass
            await asyncio.sleep(interval)
        raise errors.AgentFailedToStartError(
            "Agent healthcheck did not succeed.", agent=agent_name
        )

    async def _notify_roster_activity_event(self, event: dict):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.roster_activity_url, json=event
                ) as response:
                    assert response.status == 200
        except (AssertionError, aiohttp.ClientError) as e:
            logger.warn("(agent-exec) Failed to notify Roster of activity event %s", e)

    async def _watch_activity_stream(self, agent_name: str):
        logger.debug(
            "(agent-exec) Activity stream acquiring handle for agent %s", agent_name
        )
        handle = self.get_agent_handle(agent_name)
        logger.debug(
            "(agent-exec) Activity stream acquired handle for agent %s", agent_name
        )
        async for activity_event in handle.activity_stream():
            logger.debug("(agent-exec) Sending activity event %s", activity_event)
            await self._notify_roster_activity_event(activity_event)
        logger.warn(
            "(agent-exec) Activity stream exited iteration for agent %s", agent_name
        )

    async def _start_activity_stream_watcher(self, agent_name: str):
        await self._wait_for_agent_healthy(agent_name)
        logger.debug(
            "(agent-exec) Starting activity stream watcher for agent %s", agent_name
        )
        self.activity_stream_tasks[agent_name] = asyncio.create_task(
            self._watch_activity_stream(agent_name)
        )
        logger.debug(
            "(agent-exec) Activity stream watcher task created for agent %s", agent_name
        )

    async def _create_agent(
        self, agent: AgentSpec, wait_for_healthy: bool = True
    ) -> AgentStatus:
        if agent.name in self.store.agents:
            raise errors.AgentAlreadyExistsError(agent=agent.name)

        try:
            if not self.client.images.list(name=agent.image):
                self.client.images.pull(agent.image)
        except docker.errors.ImageNotFound as e:
            raise errors.AgentImageNotFoundError(image=agent.image) from e
        except docker.errors.APIError as e:
            raise errors.RosterError("Could not pull image.") from e

        try:
            self._push_expected_events(
                ExpectedStatusEvent.docker_start(
                    agent_name=agent.name,
                )
            )
            container = self.client.containers.run(
                agent.image,
                detach=True,
                labels=self._labels_for_agent(agent),
                # TODO: figure out user-defined network to allow specific service access only
                network_mode="default",
                ports={"8000/tcp": None},
                environment={
                    "ROSTER_RUNTIME_IP": self.docker_host_ip,
                    "ROSTER_AGENT_NAME": agent.name,
                    "ROSTER_AGENT_PORT": "8000",
                    "ROSTER_AGENT_LOG_FILE": "/var/log/roster-agent.log",
                    # TODO: figure out non-roster environment variables
                    "OPENAI_API_KEY": os.getenv("ROSTER_OPENAI_API_KEY"),
                },
            )
            container.reload()
        except docker.errors.APIError as e:
            # We no longer expect the docker start event since we assume startup failed
            self._pop_expected_event(agent_name=agent.name, action="start")
            raise errors.RosterError(f"Could not create agent {agent.name}.") from e

        self._add_agent_from_container(container)
        if wait_for_healthy:
            await self._wait_for_agent_healthy(agent.name)

        await self._start_activity_stream_watcher(agent.name)

        return self.store.agents[agent.name]

    async def create_agent(
        self, agent: AgentSpec, wait_for_healthy: bool = True
    ) -> AgentStatus:
        async with self.get_agent_lock(agent.name):
            return await self._create_agent(agent, wait_for_healthy=wait_for_healthy)

    async def _update_agent(self, agent: AgentSpec) -> AgentStatus:
        # NOTE: delete then recreate strategy is used for simplicity
        #   but will kill all running tasks
        try:
            await self._delete_agent(agent.name)
        except errors.RosterError:
            raise errors.RosterError(f"Could not update agent {agent.name}.")

        return await self._create_agent(agent)

    async def update_agent(self, agent: AgentSpec) -> AgentStatus:
        async with self.get_agent_lock(agent.name):
            return await self._update_agent(agent)

    async def _delete_agent(self, name: str) -> None:
        try:
            agent = self.store.agents[name]
            self.store.delete_agent(name)
        except KeyError:
            raise errors.AgentNotFoundError(agent=name)

        if not agent.container:
            raise errors.AgentNotFoundError(agent=name)

        if (
            name in self.activity_stream_tasks
            and not self.activity_stream_tasks[name].cancelled()
        ):
            self.activity_stream_tasks[name].cancel()

        try:
            container = self.client.containers.get(agent.container.id)
        except docker.errors.NotFound:
            raise errors.AgentNotFoundError(agent=name)

        try:
            self._push_expected_events(
                *ExpectedStatusEvent.docker_delete(agent_name=name)
            )
            container.stop()
            container.remove()
        except docker.errors.APIError as e:
            self._pop_expected_events(
                *ExpectedStatusEvent.docker_delete(agent_name=name)
            )
            raise errors.RosterError(f"Could not delete agent {name}.") from e

    async def delete_agent(self, name: str) -> None:
        async with self.get_agent_lock(name):
            await self._delete_agent(name)

    def get_agent_handle(self, name: str) -> AgentHandle:
        port = self._get_service_port_for_agent(name)
        return HttpAgentHandle.build(name, f"http://localhost:{port}")

    def _find_agent_by_container_name(
        self, container_name: str
    ) -> Optional[AgentStatus]:
        for agent in self.store.agents.values():
            if agent.container is not None and agent.container.name == container_name:
                return agent

    def _handle_docker_start_event(self, event: dict) -> Optional[ResourceStatusEvent]:
        try:
            agent_name = event["Actor"]["Attributes"][self.ROSTER_CONTAINER_LABEL]
            container_name = event["Actor"]["Attributes"]["name"]
            container = self.client.containers.get(container_name)
        except (KeyError, docker.errors.NotFound):
            return None

        if agent_name in self.store.agents:
            existing_container = self.store.agents[agent_name].container
            should_remove = (
                existing_container is not None
                and existing_container.name != container_name
            )
            if should_remove:
                # This is an unexpected container claiming to be one of our agents,
                # so we should remove it.
                logger.warn(
                    "Unexpected container claiming to be agent %s; Removing.",
                    agent_name,
                )
                try:
                    container.stop()
                    container.remove()
                    logger.debug("(docker-evt) Removed container %s", container_name)
                except docker.errors.NotFound:
                    pass
        else:
            # This is a new container, so we should update the agent status and notify listeners.
            updated_agent = AgentStatus(
                name=agent_name,
                executor=self.KEY,
                status=container.status,
                container=serialize_agent_container(container),
            )
            logger.debug("(docker-evt) New agent %s", agent_name)
            self.store.put_agent(updated_agent, notify=True)

    def _handle_docker_stop_event(self, event: dict):
        try:
            agent_name = event["Actor"]["Attributes"][self.ROSTER_CONTAINER_LABEL]
            container_name = event["Actor"]["Attributes"]["name"]
            container = self.client.containers.get(container_name)
        except (KeyError, docker.errors.NotFound):
            return None

        # If we don't know about this agent, we don't care.
        if agent_name not in self.store.agents:
            return None

        # Otherwise, we should update the agent status and notify listeners.
        updated_agent = AgentStatus(
            name=agent_name,
            executor=self.KEY,
            status=container.status,
            container=serialize_agent_container(container),
        )
        logger.debug("(docker-evt) Agent stopped %s", agent_name)
        self.store.put_agent(updated_agent, notify=True)

    def _handle_docker_kill_event(self, event: dict):
        try:
            agent_name = event["Actor"]["Attributes"][self.ROSTER_CONTAINER_LABEL]
        except (KeyError, docker.errors.NotFound):
            return None

        # If we don't know about this agent, we don't care.
        if agent_name not in self.store.agents:
            return None

        # Otherwise, we should remove the agent status and notify listeners.
        logger.debug("(docker-evt) Agent killed %s", agent_name)
        self.store.delete_agent(agent_name, notify=True)

    async def _handle_docker_event(self, event: dict):
        logger.debug("(docker-evt) Received: %s", event)
        if event["Type"] != "container":
            return
        try:
            agent_name = event["Actor"]["Attributes"][self.ROSTER_CONTAINER_LABEL]
        except (KeyError, docker.errors.NotFound):
            return None

        # Dedupe events which we triggered ourselves
        expected_event = self._pop_expected_event(
            agent_name=agent_name, action=event["Action"]
        )
        if expected_event:
            logger.debug("(docker-evt) Skipping Expected Event: %s", expected_event)
            return

        if event["Action"] == "start":
            self._handle_docker_start_event(event)
        elif event["Action"] == "stop":
            self._handle_docker_stop_event(event)
        elif event["Action"] in ["die", "destroy"]:
            self._handle_docker_kill_event(event)

    def add_status_listener(self, listener: Callable[[ResourceStatusEvent], None]):
        self.store.add_status_listener(listener)

    def remove_status_listener(self, listener: Callable[[ResourceStatusEvent], None]):
        self.store.remove_status_listener(listener)
