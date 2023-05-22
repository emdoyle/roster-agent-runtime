from typing import Callable, Union

from roster_agent_runtime import settings
from roster_agent_runtime.informers.base import Informer
from roster_agent_runtime.listeners.base import EventListener
from roster_agent_runtime.models.agent import AgentCapabilities, AgentSpec
from roster_agent_runtime.models.conversation import ConversationSpec
from roster_agent_runtime.models.task import TaskSpec

RosterSpec = Union[AgentSpec, TaskSpec, ConversationSpec]


class RosterInformer(Informer[RosterSpec]):
    def __init__(self, api_url: str = settings.ROSTER_API_EVENTS_URL):
        self.agents: dict[str, AgentSpec] = {}
        self.tasks: dict[str, TaskSpec] = {}
        self.conversations: dict[str, ConversationSpec] = {}
        self.roster_listener: EventListener = EventListener(api_url)
        self.event_listeners: list[Callable[[RosterSpec], None]] = []

    async def setup(self):
        # TODO: connect to roster API server via roster_listener
        # For now, using mock data
        self.agents = {
            "Alice": AgentSpec(
                image="langchain-roster",
                name="Alice",
                capabilities=AgentCapabilities(network_access=True),
            )
        }
        self.tasks = {
            "MyTask": TaskSpec(
                agent_name="Alice",
                name="MyTask",
                description="My task description",
            )
        }

    async def teardown(self):
        pass

    def add_event_listener(self, callback: Callable[[RosterSpec], None]):
        self.event_listeners.append(callback)

    def list(self) -> list[RosterSpec]:
        return [
            *self.agents.values(),
            *self.tasks.values(),
            *self.conversations.values(),
        ]

    # TODO: Consider removing this from the Informer interface entirely
    def get(self, id: str) -> RosterSpec:
        try:
            return self.agents[id]
        except KeyError:
            pass
        try:
            return self.tasks[id]
        except KeyError:
            pass
        try:
            return self.conversations[id]
        except KeyError:
            pass
        raise KeyError(id)
