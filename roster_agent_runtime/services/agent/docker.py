from roster_agent_runtime.models.agent import (
    AgentCapabilities,
    AgentContainer,
    AgentResource,
)
from roster_agent_runtime.services.agent import errors
from roster_agent_runtime.services.agent.base import AgentService

import docker


def serialize_agent_container(
    container: "docker.models.containers.Container",
) -> AgentContainer:
    agent_name = container.labels.get("agent_name", "Unknown Agent")
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


class DockerAgentService(AgentService):
    ROSTER_CONTAINER_LABEL = "roster-agent"

    def __init__(self):
        try:
            self.client = docker.from_env()
        except docker.errors.DockerException as e:
            raise errors.AgentServiceError("Could not connect to Docker daemon.") from e

    def list_agents(self) -> list[AgentContainer]:
        containers = self.client.containers.list(
            all=True, filters={"label": self.ROSTER_CONTAINER_LABEL}
        )
        return list(map(serialize_agent_container, containers))

    def get_agent(self, id: str) -> AgentContainer:
        try:
            container = self.client.containers.get(id)
        except docker.errors.NotFound as e:
            raise errors.AgentNotFoundError(
                f"Agent with id {id} not found.", agent=id
            ) from e
        return serialize_agent_container(container)

    def delete_agent(self, id: str) -> AgentContainer:
        try:
            container = self.client.containers.get(id)
            container.remove(force=True)
        except docker.errors.NotFound as e:
            raise errors.AgentNotFoundError(
                f"Agent with id {id} not found.", agent=id
            ) from e
        serialized_container = serialize_agent_container(container)
        serialized_container.status = "deleted"
        return serialized_container

    def start_agent(self, id: str) -> AgentContainer:
        try:
            container = self.client.containers.get(id)
            container.start()
        except docker.errors.NotFound as e:
            raise errors.AgentNotFoundError(
                f"Agent with id {id} not found.", agent=id
            ) from e
        return self.get_agent(id)

    def stop_agent(self, id: str) -> AgentContainer:
        try:
            container = self.client.containers.get(id)
            container.stop()
        except docker.errors.NotFound as e:
            raise errors.AgentNotFoundError(
                f"Agent with id {id} not found.", agent=id
            ) from e
        return self.get_agent(id)

    def create_agent(self, agent: AgentResource) -> AgentContainer:
        network_mode = "default" if agent.capabilities.network_access else "none"

        try:
            container = self.client.containers.create(
                agent.image,
                network_mode=network_mode,
                labels={
                    self.ROSTER_CONTAINER_LABEL: "True",
                    "messaging_access": str(agent.capabilities.messaging_access),
                    "agent_name": agent.name,
                },
            )
        except docker.errors.ImageNotFound as e:
            raise errors.AgentImageNotFoundError(image=agent.image) from e

        return serialize_agent_container(container)
