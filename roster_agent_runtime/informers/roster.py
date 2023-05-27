from typing import Callable, Optional

import aiohttp
from pydantic import BaseModel, Field
from roster_agent_runtime import settings
from roster_agent_runtime.informers.base import Informer
from roster_agent_runtime.informers.events.spec import (
    RosterResourceEvent, RosterSpec, deserialize_resource_event)
from roster_agent_runtime.listeners.base import EventListener
from roster_agent_runtime.logs import app_logger
from roster_agent_runtime.models.agent import AgentResource, AgentSpec
from roster_agent_runtime.models.conversation import (ConversationResource,
                                                      ConversationSpec)
from roster_agent_runtime.models.task import TaskResource, TaskSpec

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


class RosterInformer(Informer[RosterResourceEvent]):
    def __init__(
        self,
        url_config: Optional[RosterAPIURLConfig] = None,
        event_params: Optional[dict] = None,
    ):
        self.agents: dict[str, AgentSpec] = {}
        self.tasks: dict[str, TaskSpec] = {}
        self.conversations: dict[str, ConversationSpec] = {}
        self.url_config: RosterAPIURLConfig = url_config or RosterAPIURLConfig()
        self.roster_listener: EventListener = EventListener(
            self.url_config.events_url,
            params=event_params or {"status_changes": False},
            middleware=[deserialize_resource_event],
            handlers=[self._handle_spec_event],
        )
        self.event_listeners: list[Callable[[RosterResourceEvent], None]] = []

    async def _load_initial_specs(self):
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(self.url_config.agents_url) as resp:
                    for agent in await resp.json():
                        spec = AgentResource(**agent).spec
                        self.agents[spec.name] = spec
            except (aiohttp.ClientError, TypeError):
                logger.error("(roster-spec) Failed to load initial agents")
            try:
                async with session.get(self.url_config.tasks_url) as resp:
                    for task in await resp.json():
                        spec = TaskResource(**task).spec
                        self.tasks[spec.name] = spec
            except (aiohttp.ClientError, TypeError):
                logger.error("(roster-spec) Failed to load initial tasks")
            try:
                async with session.get(self.url_config.conversations_url) as resp:
                    for conversation in await resp.json():
                        spec = ConversationResource(**conversation).spec
                        self.conversations[spec.name] = spec
            except (aiohttp.ClientError, TypeError):
                logger.error("(roster-spec) Failed to load initial conversations")

    async def setup(self):
        logger.debug("Setting up Roster Informer")
        self.roster_listener.run_as_task()
        await self._load_initial_specs()

    async def teardown(self):
        logger.debug("Tearing down Roster Informer")
        self.roster_listener.stop()

    def _handle_put_spec_event(self, event: RosterResourceEvent):
        if event.resource_type == "AGENT":
            self.agents[event.name] = event.resource.spec
        elif event.resource_type == "TASK":
            self.tasks[event.name] = event.resource.spec
        elif event.resource_type == "CONVERSATION":
            self.conversations[event.name] = event.resource.spec
        else:
            logger.warn("(roster-spec) Unknown resource type: %s", event)

    def _handle_delete_spec_event(self, event: RosterResourceEvent):
        if event.resource_type == "AGENT":
            self.agents.pop(event.name, None)
        elif event.resource_type == "TASK":
            self.tasks.pop(event.name, None)
        elif event.resource_type == "CONVERSATION":
            self.conversations.pop(event.name, None)
        else:
            logger.warn("(roster-spec) Unknown resource type: %s", event)

    def _handle_spec_event(self, event: RosterResourceEvent):
        logger.debug("(roster-spec) Received Spec event: %s", event)
        if event.event_type == "PUT":
            self._handle_put_spec_event(event)
        elif event.event_type == "DELETE":
            self._handle_delete_spec_event(event)
        else:
            logger.warn("(roster-spec) Unknown event: %s", event)
        logger.debug("(roster-spec) Pushing Spec event to listeners: %s", event)
        for listener in self.event_listeners:
            listener(event)

    def add_event_listener(self, callback: Callable[[RosterResourceEvent], None]):
        self.event_listeners.append(callback)

    def list(self) -> list[RosterSpec]:
        return [
            *self.agents.values(),
            *self.tasks.values(),
            *self.conversations.values(),
        ]
