import json
import os
import platform

import websockets
from roster_agent_runtime.models.agent import (
    AgentCapabilities,
    AgentContainer,
    AgentResource,
)
from roster_agent_runtime.models.conversation import (
    ConversationMessage,
    ConversationPrompt,
    ConversationResource,
)
from roster_agent_runtime.models.task import TaskResource
from roster_agent_runtime.services.agent import errors
from roster_agent_runtime.services.agent.base import AgentService
from roster_agent_runtime.util import aretry
from websocket import WebSocket

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
class DockerAgentService(AgentService):
    ROSTER_CONTAINER_LABEL = "roster-agent"

    def __init__(self):
        try:
            self.client = docker.from_env()
            # consider using docker-py's events API to keep this up to date
            # also consider using sqlite to persist this data
            self.agents: dict[str, AgentResource] = {}
            self.tasks: dict[str, TaskResource] = {}
            self.conversations: dict[str, tuple[ConversationResource, WebSocket]] = {}
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

    async def create_agent(self, agent: AgentResource) -> AgentResource:
        if agent.name in self.agents:
            raise errors.AgentAlreadyExistsError(agent=agent.name)
        self.agents[agent.name] = agent
        if not self.client.images.list(name=agent.image):
            try:
                self.client.images.pull(agent.image)
            except docker.errors.ImageNotFound as e:
                raise errors.AgentImageNotFoundError(image=agent.image) from e
        agent.status = "ready"
        return agent

    async def list_agents(self) -> list[AgentResource]:
        return list(self.agents.values())

    async def get_agent(self, name: str) -> AgentResource:
        try:
            return self.agents[name]
        except KeyError as e:
            raise errors.AgentNotFoundError(agent=name) from e

    async def delete_agent(self, name: str) -> AgentResource:
        try:
            agent = self.agents.pop(name)
        except KeyError as e:
            raise errors.AgentNotFoundError(agent=name) from e

        containers = self.client.containers.list(
            all=True, filters={"label": f"{self.ROSTER_CONTAINER_LABEL}={name}"}
        )
        # NOTE: This may partially complete before raising an error
        for container in containers:
            try:
                container.remove(force=True)
            except docker.errors.APIError as e:
                raise errors.AgentServiceError(f"Could not delete agent {name}.") from e
        agent.status = "deleted"
        return agent

    async def initiate_task(self, name: str, task: TaskResource) -> TaskResource:
        """if the agent exists, use the AgentResource to run a container for the task"""
        try:
            agent = self.agents[name]
        except KeyError as e:
            raise errors.AgentNotFoundError(agent=name) from e

        try:
            if agent.capabilities.network_access:
                network_mode = "default"
            else:
                network_mode = None

            container = self.client.containers.run(
                agent.image,
                detach=True,
                labels=self._labels_for_agent(agent),
                network_mode=network_mode,
                environment={
                    "ROSTER_RUNTIME_IP": self.host_ip,
                    "ROSTER_AGENT_NAME": name,
                    "ROSTER_AGENT_TASK_ID": task.id,
                    "ROSTER_AGENT_TASK_NAME": task.name,
                    "ROSTER_AGENT_TASK_DESCRIPTION": task.description,
                },
            )
        except docker.errors.APIError as e:
            raise errors.AgentServiceError(
                f"Could not initiate task {task.name} on agent {name}."
            ) from e
        task.status = "running"
        task.container = serialize_agent_container(container)
        return task

    async def start_conversation(
        self, name: str, conversation: ConversationResource
    ) -> ConversationResource:
        try:
            agent = self.agents[name]
        except KeyError as e:
            raise errors.AgentNotFoundError(agent=name) from e

        if conversation.id in self.conversations:
            raise errors.ConversationAlreadyExistsError(conversation=conversation.id)

        try:
            # TODO: figure out websocket connection with no network capabilities
            container = self.client.containers.run(
                agent.image,
                detach=True,
                labels=self._labels_for_agent(agent),
                ports={"8000/tcp": None},
                environment={
                    "ROSTER_RUNTIME_IP": self.host_ip,
                    "ROSTER_AGENT_NAME": name,
                    "ROSTER_AGENT_CONVERSATION_ID": conversation.id,
                    "ROSTER_AGENT_CONVERSATION_NAME": conversation.name,
                    "ROSTER_AGENT_CONVERSATION_PORT": "8000",
                    # TODO: how is non-roster env passed to agents?
                    "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
                },
            )
        except docker.errors.APIError as e:
            raise errors.AgentServiceError(
                f"Could not start conversation {conversation.name} on agent {name}."
            ) from e

        container.reload()

        async def _connect():
            return await websockets.connect(
                f"ws://localhost:{container.ports['8000/tcp'][0]['HostPort']}"
            )

        connection = await aretry(_connect)
        self.conversations[conversation.id] = (conversation, connection)

        conversation.status = "running"
        conversation.container = serialize_agent_container(container)
        return conversation

    async def prompt(
        self, name: str, conversation_id: str, conversation_prompt: ConversationPrompt
    ) -> ConversationResource:
        try:
            conversation, ws_conn = self.conversations[conversation_id]
        except KeyError as e:
            raise errors.ConversationNotFoundError(conversation=conversation_id) from e
        if conversation.agent_name != name:
            raise errors.ConversationNotFoundError(conversation=conversation_id)
        try:
            # TODO: send full prompt message, decode in agent
            await ws_conn.send(conversation_prompt.message.message)
            conversation.history.append(conversation_prompt.message)
            response = await ws_conn.recv()
            message = ConversationMessage(
                sender=conversation.agent_name, message=response
            )
            conversation.history.append(message)
        except websockets.WebSocketException as e:
            raise errors.AgentServiceError(
                f"Could not prompt conversation {conversation_id} on agent {name}."
            ) from e
        except TypeError as e:
            raise errors.AgentServiceError(
                f"Could not parse response from conversation {conversation_id} on agent {name}."
            ) from e
        return conversation

    async def end_conversation(
        self, name: str, conversation_id: str
    ) -> ConversationResource:
        try:
            conversation = self.conversations.pop(conversation_id)
        except KeyError as e:
            raise errors.ConversationNotFoundError(conversation=conversation_id) from e
        if conversation[0].agent_name != name:
            raise errors.ConversationNotFoundError(conversation=conversation_id)
        try:
            conversation[1].close()
            container = self.client.containers.get(conversation[0].container.id)
            container.remove(force=True)
        except docker.errors.APIError as e:
            raise errors.AgentServiceError(
                f"Could not end conversation {conversation_id} on agent {name}."
            ) from e
        conversation[0].status = "ended"
        return conversation[0]
