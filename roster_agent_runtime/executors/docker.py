import platform

from roster_agent_runtime.executors.base import AgentExecutor
from roster_agent_runtime.models.agent import (
    AgentCapabilities,
    AgentContainer,
    AgentResource,
)
from roster_agent_runtime.models.conversation import (
    ConversationPrompt,
    ConversationResource,
)
from roster_agent_runtime.models.task import TaskResource
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


# Is this still necessary?
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

    def create_agent(self, agent: AgentResource) -> AgentResource:
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
            # Serialize docker container into the AgentResource?
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
                },
            )
        except docker.errors.APIError as e:
            raise errors.AgentServiceError(
                f"Could not create agent {agent.name}."
            ) from e

        agent.status = "ready"
        return agent

    def delete_agent(self, agent: AgentResource) -> AgentResource:
        containers = self.client.containers.list(
            all=True, filters={"label": f"{self.ROSTER_CONTAINER_LABEL}={agent.name}"}
        )
        # NOTE: This may partially complete before raising an error if there are multiple containers
        for container in containers:
            try:
                container.remove(force=True)
            except docker.errors.APIError as e:
                raise errors.AgentServiceError(
                    f"Could not delete agent {agent.name}."
                ) from e

        agent.status = "deleted"
        return agent

    async def initiate_task(self, task: TaskResource) -> TaskResource:
        # make HTTP request to agent to start task
        #   find agent's container
        #   read host port assigned to container (could also generate this and set directly)
        #   make HTTP request to container at host:port

        task.status = "running"
        return task

    async def prompt(
        self,
        conversation: ConversationResource,
        conversation_prompt: ConversationPrompt,
    ) -> ConversationResource:
        conversation.history.append(conversation_prompt.message)
        # make HTTP request to agent to start task
        #   find agent's container
        #   read host port assigned to container (could also generate this and set directly)
        #   make HTTP request to container at host:port

        return conversation
