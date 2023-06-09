import asyncio

from roster_agent_runtime import errors
from roster_agent_runtime.controllers.agent.store import AgentControllerStore
from roster_agent_runtime.controllers.events.status import ControllerStatusEvent
from roster_agent_runtime.executors import AgentExecutor
from roster_agent_runtime.executors.events import (
    EventType,
    ExecutorStatusEvent,
    Resource,
)
from roster_agent_runtime.informers.events.spec import RosterResourceEvent
from roster_agent_runtime.informers.roster import RosterInformer
from roster_agent_runtime.logs import app_logger
from roster_agent_runtime.models.agent import AgentSpec, AgentStatus
from roster_agent_runtime.notifier import RosterNotifier

logger = app_logger()


class AgentController:
    def __init__(
        self,
        executor: AgentExecutor,
        roster_informer: RosterInformer,
        roster_notifier: RosterNotifier,
    ):
        # TODO: support multiple AgentExecutors/Pools
        self.executor = executor
        self.roster_informer = roster_informer
        self.roster_notifier = roster_notifier
        self.store = AgentControllerStore(
            status_listeners=[self._notify_roster_status_event]
        )

        # Synchronization primitives
        self.reconciliation_queue = asyncio.Queue()
        self.reconciliation_task = None
        self.lock = asyncio.Lock()

    @property
    def desired(self):
        return self.store.desired

    @property
    def current(self):
        return self.store.current

    async def setup(self):
        logger.debug("(agent-control) Setup started.")
        try:
            self.roster_notifier.setup()
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
            self.roster_notifier.teardown()
            await asyncio.gather(
                self.roster_informer.teardown(), self.executor.teardown()
            )
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
        await self.roster_informer.setup()
        self.load_initial_spec()

    async def setup_executor_connection(self):
        # Setup listeners on Executor for resource status (current state)
        self.setup_status_listeners()
        await self.executor.setup()
        self.load_initial_status()

    def load_initial_spec(self):
        # Load full desired state from Roster API
        for spec in self.roster_informer.list():
            if isinstance(spec, AgentSpec):
                self.desired.agents[spec.name] = spec

    def load_initial_status(self):
        # Load full current state from Executor
        for status in self.executor.list_agents():
            self.store.put_agent(status.name, status)

    def _handle_put_spec_event(self, event: RosterResourceEvent):
        if event.resource_type == "AGENT":
            self.desired.agents[event.name] = event.resource.spec
        else:
            logger.warn(
                "(agent-control) Unknown spec event resource type from Roster API: %s",
                event.resource_type,
            )

    def _handle_delete_spec_event(self, event: RosterResourceEvent):
        if event.resource_type == "AGENT":
            self.desired.agents.pop(event.name, None)
        else:
            logger.warn(
                "(agent-control) Unknown spec event resource type from Roster API: %s",
                event.resource_type,
            )

    async def _serial_handle_spec_event(self, event: RosterResourceEvent):
        async with self.lock:
            logger.info("Received spec event: %s", event)
            if event.event_type == "PUT":
                self._handle_put_spec_event(event)
            elif event.event_type == "DELETE":
                self._handle_delete_spec_event(event)
            else:
                logger.warn("(agent-control) Unknown event: %s", event)
        self.reconciliation_queue.put_nowait(True)

    def _handle_spec_event(self, event: RosterResourceEvent):
        asyncio.create_task(self._serial_handle_spec_event(event))

    def setup_spec_listeners(self):
        self.roster_informer.add_event_listener(self._handle_spec_event)

    def setup_status_listeners(self):
        self.executor.add_event_listener(self._handle_status_event)

    def _handle_agent_status_event(self, event: ExecutorStatusEvent):
        if event.event_type == EventType.PUT:
            try:
                agent = event.get_agent_status()
                self.store.put_agent(event.name, agent)
            except ValueError:
                return
        elif event.event_type == EventType.DELETE:
            try:
                self.store.delete_agent(event.name)
            except errors.AgentNotFoundError:
                return
        self.reconciliation_queue.put_nowait(True)

    def _handle_status_event(self, event: ExecutorStatusEvent):
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
            return image_matches and agent.container.capabilities == spec.capabilities
        # Should probably raise if there is no container
        # but this implies reconsidering whether it is optional
        return True

    async def reconcile_agents(self):
        logger.debug("(rec-agents) Reconciling agents...")
        logger.debug("(rec-agents) Current agents: %s", self.current.agents)
        logger.debug("(rec-agents) Desired agents: %s", self.desired.agents)
        for name, spec in self.desired.agents.items():
            if name not in self.current.agents:
                await self.create_agent(spec)
            elif not self.agent_matches_spec(self.current.agents[name], spec):
                await self.update_agent(spec)
        current_agents = list(self.current.agents.items())
        for name, agent in current_agents:
            if name not in self.desired.agents:
                await self.delete_agent(agent.name)
        logger.debug("(rec-agents) Final agents: %s", self.current.agents)

    async def create_agent(self, agent: AgentSpec) -> AgentStatus:
        if agent.name in self.current.agents:
            raise errors.AgentAlreadyExistsError(agent=agent.name)
        self.store.put_agent(agent.name, await self.executor.create_agent(agent))
        status = self.current.agents[agent.name]
        logger.info("Created agent %s", agent.name)
        return status

    async def update_agent(self, agent: AgentSpec) -> AgentStatus:
        if agent.name not in self.current.agents:
            raise errors.AgentNotFoundError(agent=agent.name)
        self.store.put_agent(agent.name, await self.executor.update_agent(agent))
        status = self.current.agents[agent.name]
        logger.info("Updated agent %s", agent.name)
        return status

    def list_agents(self) -> list[AgentStatus]:
        return list(self.current.agents.values())

    def get_agent(self, name: str) -> AgentStatus:
        try:
            return self.current.agents[name]
        except KeyError as e:
            raise errors.AgentNotFoundError(agent=name) from e

    async def delete_agent(self, name: str) -> None:
        try:
            await self.executor.delete_agent(name)
            self.store.delete_agent(name)
            logger.info("Deleted agent %s", name)
        except errors.AgentNotFoundError:
            pass
