import json

import websocket
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

import docker


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


# TODO: Consider using a websocket client library; make interface async
class DockerAgentService(AgentService):
    ROSTER_CONTAINER_LABEL = "roster-agent"

    def __init__(self):
        try:
            self.client = docker.from_env()
            # consider using docker-py's events API to keep this up to date
            # also consider using sqlite to persist this data
            self.agents = {}
            self.tasks = {}
            self.conversations = {}
        except docker.errors.DockerException as e:
            raise errors.AgentServiceError("Could not connect to Docker daemon.") from e

    def create_agent(self, agent: AgentResource) -> AgentResource:
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

    def list_agents(self) -> list[AgentResource]:
        return list(self.agents.values())

    def get_agent(self, name: str) -> AgentResource:
        try:
            return self.agents[name]
        except KeyError as e:
            raise errors.AgentNotFoundError(agent=name) from e

    def delete_agent(self, name: str) -> AgentResource:
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

    def initiate_task(self, name: str, task: TaskResource) -> TaskResource:
        """if the agent exists, use the AgentResource to run a container for the task"""
        try:
            agent = self.agents[name]
        except KeyError as e:
            raise errors.AgentNotFoundError(agent=name) from e

        try:
            """check network_access capabilities from agent and set network_mode accordingly"""
            if agent.capabilities.network_access:
                network_mode = "default"
            else:
                network_mode = None
            container = self.client.containers.run(
                agent.image,
                detach=True,
                labels={self.ROSTER_CONTAINER_LABEL: name},
                network_mode=network_mode,
                environment={
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

    def start_conversation(
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
                labels={self.ROSTER_CONTAINER_LABEL: name},
                ports={"8000/tcp": None},
                environment={
                    "ROSTER_AGENT_NAME": name,
                    "ROSTER_AGENT_CONVERSATION_ID": conversation.id,
                    "ROSTER_AGENT_CONVERSATION_NAME": conversation.name,
                    "ROSTER_AGENT_CONVERSATION_PORT": "8000",
                },
            )
        except docker.errors.APIError as e:
            raise errors.AgentServiceError(
                f"Could not start conversation {conversation.name} on agent {name}."
            ) from e

        # TODO: actually need to wait for the websocket server to start up and become healthy

        try:
            ws_conn = websocket.create_connection(
                f"ws://localhost:{container.ports['8000/tcp'][0]}"
            )
        except websocket.WebSocketException as e:
            raise errors.AgentServiceError(
                f"Could not connect to conversation {conversation.id} on agent {name}."
            ) from e
        conversation.status = "running"
        conversation.container = serialize_agent_container(container)
        self.conversations[conversation.id] = (conversation, ws_conn)
        return conversation

    def prompt(
        self, name: str, conversation_id: str, conversation_prompt: ConversationPrompt
    ) -> ConversationResource:
        try:
            conversation = self.conversations[conversation_id]
        except KeyError as e:
            raise errors.ConversationNotFoundError(conversation=conversation_id) from e
        if conversation[0].agent_name != name:
            raise errors.ConversationNotFoundError(conversation=conversation_id)
        try:
            conversation[1].send(json.dumps(conversation_prompt.message.dict()))
            response = conversation[1].recv()
            message = ConversationMessage(**json.loads(response))
            conversation[0].history.append(message)
        except websocket.WebSocketException as e:
            raise errors.AgentServiceError(
                f"Could not prompt conversation {conversation_id} on agent {name}."
            ) from e
        except TypeError as e:
            raise errors.AgentServiceError(
                f"Could not parse response from conversation {conversation_id} on agent {name}."
            ) from e
        return conversation[0]

    def end_conversation(self, name: str, conversation_id: str) -> ConversationResource:
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
