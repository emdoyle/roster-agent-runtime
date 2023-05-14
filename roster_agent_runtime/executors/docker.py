import os
import platform

import aiohttp
from roster_agent_runtime.executors.base import AgentExecutor
from roster_agent_runtime.models.agent import (
    AgentCapabilities,
    AgentContainer,
    AgentResource,
)
from roster_agent_runtime.models.conversation import (
    ConversationMessage,
    ConversationResource,
)
from roster_agent_runtime.models.task import TaskResource
from roster_agent_runtime.services.agent import errors

import docker


# TODO: consider sending requests directly to Roster API Server?
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
    agent_name = container.labels.get("roster-agent", "Unknown Agent")
    capabilities = AgentCapabilities(
        network_access=container.attrs["HostConfig"]["NetworkMode"] == "default",
        messaging_access=container.labels.get("messaging_access", False) == "True",
    )
    return AgentContainer(
        id=container.id,
        name=container.name,
        agent_name=agent_name,
        image=container.image.tags[0],
        status=container.status,
        labels=container.labels,
        capabilities=capabilities,
    )


# TODO: make docker client operations async
class DockerAgentExecutor(AgentExecutor):
    ROSTER_CONTAINER_LABEL = "roster-agent"

    def __init__(self):
        try:
            self.client = docker.from_env()
            self.agent_containers: dict[str, AgentContainer] = {}
        except docker.errors.DockerException as e:
            raise errors.AgentServiceError("Could not connect to Docker daemon.") from e

    @property
    def host_ip(self):
        return get_host_ip(client=self.client)

    def _labels_for_agent(self, agent: AgentResource) -> dict:
        return {
            self.ROSTER_CONTAINER_LABEL: agent.name,
            "messaging_access": str(agent.capabilities.messaging_access),
        }

    def _get_service_port_for_agent(self, name: str) -> int:
        container = self.agent_containers.get(name)
        if not container:
            # TODO: fallback to docker API calls
            raise errors.AgentNotFoundError(agent=name)

        try:
            container = self.client.containers.get(container.id)
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

    async def create_agent(self, agent: AgentResource) -> AgentResource:
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

        self.agent_containers[agent.name] = serialize_agent_container(container)

        agent.status = "ready"
        return agent

    async def delete_agent(self, agent: AgentResource) -> AgentResource:
        container = self.agent_containers.get(agent.name)
        if not container:
            raise errors.AgentNotFoundError(agent=agent.name)

        try:
            container = self.client.containers.get(container.id)
        except docker.errors.NotFound:
            raise errors.AgentNotFoundError(agent=agent.name)

        try:
            container.remove(force=True)
        except docker.errors.APIError as e:
            raise errors.AgentServiceError(
                f"Could not delete agent {agent.name}."
            ) from e

        agent.status = "deleted"
        return agent

    async def initiate_task(self, task: TaskResource) -> TaskResource:
        port = self._get_service_port_for_agent(task.agent_name)
        url = f"http://localhost:{port}/execute_task"

        payload = {"name": task.name, "description": task.description}

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                assert response.status == 200

        task.status = "running"
        return task

    async def prompt(
        self,
        conversation: ConversationResource,
        conversation_message: ConversationMessage,
    ) -> ConversationResource:
        conversation.history.append(conversation_message)
        port = self._get_service_port_for_agent(conversation.agent_name)
        url = f"http://localhost:{port}/chat"

        payload = [message.dict() for message in conversation.history]

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                assert response.status == 200

        return conversation
