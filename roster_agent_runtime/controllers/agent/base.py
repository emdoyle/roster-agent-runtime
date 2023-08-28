import asyncio
from copy import copy
from typing import Optional

from roster_agent_runtime import errors
from roster_agent_runtime.agents.pool import AgentPool
from roster_agent_runtime.controllers.agent.store import AgentControllerStore
from roster_agent_runtime.controllers.events.status import ControllerStatusEvent
from roster_agent_runtime.executors.events import (
    EventType,
    Resource,
    ResourceStatusEvent,
)
from roster_agent_runtime.informers.events.spec import RosterResourceEvent
from roster_agent_runtime.informers.roster import RosterInformer
from roster_agent_runtime.logs import app_logger
from roster_agent_runtime.models.agent import AgentSpec, AgentStatus
from roster_agent_runtime.notifier import RosterNotifier
from roster_agent_runtime.singletons import get_roster_informer, get_roster_notifier

logger = app_logger()


class AgentController:
    def __init__(
        self,
        pool: AgentPool,
        roster_informer: Optional[RosterInformer] = None,
        roster_notifier: Optional[RosterNotifier] = None,
    ):
        self.pool = pool
        self.roster_informer = roster_informer or get_roster_informer()
        self.roster_notifier = roster_notifier or get_roster_notifier()
        self.store = AgentControllerStore(
            status_listeners=[self._notify_roster_status_event]
        )

        # Synchronization primitives
        self.reconciliation_queue = asyncio.Queue()
        self.reconciliation_task = None
        self.lock = asyncio.Lock()

    async def setup(self):
        logger.debug("(agent-control) Setup started.")
        try:
            await asyncio.gather(
                self.setup_roster_connection(),
                self.setup_executor_connection(),
            )
            logger.debug("(agent-control) Connection setup complete.")
            await self.reconcile()
        except Exception as e:
            await self.teardown()
            raise errors.SetupError from e
        logger.debug("(agent-control) Setup complete.")

    async def run(self):
        self.reconciliation_task = asyncio.create_task(self.reconcile_loop())
        await self.reconciliation_task

    async def teardown(self):
        logger.debug("(agent-control) Teardown started.")
        try:
            if self.reconciliation_task is not None:
                self.reconciliation_task.cancel()
                self.reconciliation_task = None
        except Exception as e:
            raise errors.TeardownError from e
        logger.debug("(agent-control) Teardown complete.")

    async def reconcile_loop(self):
        logger.debug("(agent-control) Starting reconciliation loop...")
        while True:
            # TODO: add safety measures (backoff etc.)
            # right now, just reconcile globally on any change
            # but later, should reconcile only the changed resource
            try:
                await self.reconciliation_queue.get()
                await self.reconcile()
            except asyncio.CancelledError:
                logger.debug("(agent-control) Reconciliation loop cancelled.")
                break
            except Exception as e:
                logger.debug("(agent-control) Error during reconciliation: %s", e)
                logger.error("Error during Agent Controller reconciliation.")

    async def setup_roster_connection(self):
        # Setup Informer for Roster API resources (desired state)
        self.setup_spec_listeners()
        self.load_initial_spec()

    async def setup_executor_connection(self):
        # Setup listeners on Executor for resource status (current state)
        self.setup_status_listeners()
        self.load_initial_status()

    def load_initial_spec(self):
        # Load full desired state from Roster API
        for spec in self.roster_informer.list():
            if isinstance(spec, AgentSpec):
                self.store.put_agent_spec(spec)

    def load_initial_status(self):
        # Load full current state from AgentPool
        for status in self.pool.list_agents():
            self.store.put_agent_status(status)

    def _handle_put_spec_event(self, event: RosterResourceEvent):
        if event.resource_type == "AGENT":
            self.store.put_agent_spec(event.resource.spec)
        else:
            logger.debug(
                "(agent-control) Unknown spec event resource type from Roster API: %s",
                event.resource_type,
            )

    def _handle_delete_spec_event(self, event: RosterResourceEvent):
        if event.resource_type == "AGENT":
            try:
                self.store.delete_agent_spec(event.name)
            except errors.AgentNotFoundError:
                return
        else:
            logger.debug(
                "(agent-control) Unknown spec event resource type from Roster API: %s",
                event.resource_type,
            )

    def _handle_spec_event(self, event: RosterResourceEvent):
        logger.info("Controller received spec event: %s", event)
        if event.event_type == "PUT":
            self._handle_put_spec_event(event)
        elif event.event_type == "DELETE":
            self._handle_delete_spec_event(event)
        else:
            logger.debug("(agent-control) Unknown event: %s", event)

        self.reconciliation_queue.put_nowait(True)

    def setup_spec_listeners(self):
        self.roster_informer.add_event_listener(self._handle_spec_event)

    def setup_status_listeners(self):
        self.pool.add_status_listener(self._handle_status_event)

    def _handle_agent_status_event(self, event: ResourceStatusEvent):
        if event.event_type == EventType.PUT:
            try:
                agent = event.get_agent_status()
                self.store.put_agent_status(agent)
            except ValueError:
                return
        elif event.event_type == EventType.DELETE:
            try:
                self.store.delete_agent_status(event.name)
            except errors.AgentNotFoundError:
                return
        self.reconciliation_queue.put_nowait(True)

    def _handle_status_event(self, event: ResourceStatusEvent):
        if event.resource_type == Resource.AGENT:
            self._handle_agent_status_event(event)
        else:
            logger.warn(
                "(agent-control) Unknown status event resource type from executor: %s",
                event,
            )

    def _notify_roster_status_event(self, event: ControllerStatusEvent):
        self.roster_notifier.push_event(event)

    async def reconcile(self):
        async with self.lock:
            logger.info("Controller reconciling...")
            await self.reconcile_agents()
            logger.info("Controller reconciled.")

    @staticmethod
    def agent_matches_spec(agent: AgentStatus, spec: AgentSpec) -> bool:
        name_matches = agent.name == spec.name
        if not name_matches:
            return False
        if agent.container is not None:
            image_matches = (
                agent.container.image == spec.image
                or agent.container.image.split(":")[0] == spec.image
            )
            return image_matches
        # Should probably raise if there is no container
        # but this implies reconsidering whether it is optional
        return True

    async def reconcile_agents(self):
        logger.debug("(rec-agents) Reconciling agents...")
        current_agents = copy(self.store.current)
        desired_agents = copy(self.store.desired)
        logger.debug("(rec-agents) Current agents: %s", current_agents)
        logger.debug("(rec-agents) Desired agents: %s", desired_agents)
        for name, spec in desired_agents.items():
            if name not in current_agents:
                await self.create_agent(spec)
            elif not self.agent_matches_spec(current_agents[name], spec):
                await self.update_agent(spec)
        for name, agent in current_agents.items():
            if name not in desired_agents:
                await self.delete_agent(agent.name)
        logger.debug("(rec-agents) Final agents: %s", self.store.current)

    async def create_agent(self, agent: AgentSpec) -> AgentStatus:
        if agent.name in self.store.current:
            raise errors.AgentAlreadyExistsError(agent=agent.name)
        agent_status = await self.pool.create_agent(agent)
        self.store.put_agent_status(agent_status)
        logger.info("Created agent %s", agent.name)
        return agent_status

    async def update_agent(self, agent: AgentSpec) -> AgentStatus:
        if agent.name not in self.store.current:
            raise errors.AgentNotFoundError(agent=agent.name)
        agent_status = await self.pool.update_agent(agent)
        self.store.put_agent_status(agent_status)
        logger.info("Updated agent %s", agent.name)
        return agent_status

    def list_agents(self) -> list[AgentStatus]:
        return list(self.store.current.values())

    async def delete_agent(self, name: str) -> None:
        try:
            await self.pool.delete_agent(name)
            self.store.delete_agent_status(name)
            logger.info("Deleted agent %s", name)
        except errors.AgentNotFoundError:
            pass
