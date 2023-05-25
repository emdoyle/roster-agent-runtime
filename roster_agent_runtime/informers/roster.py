from typing import Callable, Optional

from pydantic import BaseModel, Field
from roster_agent_runtime import settings
from roster_agent_runtime.informers.base import Informer
from roster_agent_runtime.informers.events.spec import (
    RosterSpec,
    RosterSpecEvent,
    deserialize_spec_event,
)
from roster_agent_runtime.listeners.base import EventListener
from roster_agent_runtime.logs import app_logger
from roster_agent_runtime.models.agent import AgentSpec
from roster_agent_runtime.models.conversation import ConversationSpec
from roster_agent_runtime.models.task import TaskSpec

logger = app_logger()


class RosterAPIURLConfig(BaseModel):
    url: str = Field(default=settings.ROSTER_API_URL, description="Roster API base URL")
    agents_url: str = Field(
        default=settings.ROSTER_API_AGENTS_URL, description="Roster API agents URL"
    )
    tasks_url: str = Field(
        default=settings.ROSTER_API_TASKS_URL, description="Roster API tasks URL"
    )
    conversations_url: str = Field(
        default=settings.ROSTER_API_CONVERSATIONS_URL,
        description="Roster API conversations URL",
    )
    events_url: str = Field(
        default=settings.ROSTER_API_EVENTS_URL, description="Roster API events URL"
    )

    class Config:
        validate_assignment = True


class RosterInformer(Informer[RosterSpecEvent]):
    def __init__(self, url_config: Optional[RosterAPIURLConfig] = None):
        self.agents: dict[str, AgentSpec] = {}
        self.tasks: dict[str, TaskSpec] = {}
        self.conversations: dict[str, ConversationSpec] = {}
        self.url_config: RosterAPIURLConfig = url_config or RosterAPIURLConfig()
        self.roster_listener: EventListener = EventListener(
            self.url_config.events_url,
            middleware=[deserialize_spec_event],
            handlers=[self._handle_spec_event],
        )
        self.event_listeners: list[Callable[[RosterSpecEvent], None]] = []

    async def setup(self):
        logger.info("Setting up Roster Informer")
        self.roster_listener.run_as_task()
        # TODO: list resources from roster API

    async def teardown(self):
        self.roster_listener.stop()

    def _handle_put_spec_event(self, event: RosterSpecEvent):
        if event.resource_type == "AGENT":
            self.agents[event.name] = event.spec
        elif event.resource_type == "TASK":
            self.tasks[event.name] = event.spec
        elif event.resource_type == "CONVERSATION":
            self.conversations[event.name] = event.spec
        else:
            logger.warn("(roster-spec) Unknown resource type: %s", event)

    def _handle_delete_spec_event(self, event: RosterSpecEvent):
        if event.resource_type == "AGENT":
            self.agents.pop(event.name, None)
        elif event.resource_type == "TASK":
            self.tasks.pop(event.name, None)
        elif event.resource_type == "CONVERSATION":
            self.conversations.pop(event.name, None)
        else:
            logger.warn("(roster-spec) Unknown resource type: %s", event)

    def _handle_spec_event(self, event: RosterSpecEvent):
        if event.event_type == "PUT":
            self._handle_put_spec_event(event)
        elif event.event_type == "DELETE":
            self._handle_delete_spec_event(event)
        else:
            logger.warn("(roster-spec) Unknown event: %s", event)
        for listener in self.event_listeners:
            listener(event)

    def add_event_listener(self, callback: Callable[[RosterSpecEvent], None]):
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
