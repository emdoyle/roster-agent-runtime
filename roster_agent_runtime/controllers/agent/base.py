import asyncio
from typing import Optional

from roster_agent_runtime.controllers.agent import errors
from roster_agent_runtime.controllers.agent.store import AgentControllerStore
from roster_agent_runtime.controllers.events.status import ControllerStatusEvent
from roster_agent_runtime.executors import AgentExecutor
from roster_agent_runtime.executors.events import EventType, ExecutorStatusEvent
from roster_agent_runtime.informers.roster import RosterInformer, RosterSpec
from roster_agent_runtime.logs import app_logger
from roster_agent_runtime.models.agent import AgentSpec, AgentStatus
from roster_agent_runtime.models.task import TaskSpec, TaskStatus
from roster_agent_runtime.notifier import RosterNotifier

logger = app_logger()

AGENT_CONTROLLER: Optional["AgentController"] = None


def get_agent_controller() -> "AgentController":
    global AGENT_CONTROLLER
    if AGENT_CONTROLLER is not None:
        return AGENT_CONTROLLER

    # This should be configurable in settings
    from roster_agent_runtime.executors.docker import DockerAgentExecutor

    AGENT_CONTROLLER = AgentController(
        executor=DockerAgentExecutor(),
        roster_informer=RosterInformer(),
        roster_notifier=RosterNotifier(),
    )
    return AGENT_CONTROLLER


# TODO: fix thread/coroutine safety throughout

# Consider separating TaskController from AgentController
# main thing is the Executor relationship
class AgentController:
    def __init__(
        self,
        executor: AgentExecutor,
        roster_informer: RosterInformer,
        roster_notifier: RosterNotifier,
    ):
        # TODO: properly abstract executor per-Agent
        self.executor = executor
        self.roster_informer = roster_informer
        self.roster_notifier = roster_notifier
        self.store = AgentControllerStore(
            status_listeners=[self._notify_roster_status_change]
        )
        self.reconciliation_queue = asyncio.Queue()
        self.reconciliation_task = None

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
            logger.debug("(agent-control) Reconciling...")
            await self.reconcile()
            logger.debug("(agent-control) Reconciled.")
            logger.debug("(agent-control) Starting reconciliation loop...")
            self.reconciliation_task = asyncio.create_task(self.reconcile_loop())
            logger.debug("(agent-control) Reconciliation loop started.")
        except Exception as e:
            await self.teardown()
            raise errors.SetupError from e
        logger.debug("(agent-control) Setup complete.")

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
        while True:
            # TODO: add safety measures (backoff etc.)
            # right now, just reconcile globally on any change
            # but later, should reconcile only the changed resource
            await self.reconciliation_queue.get()
            await self.reconcile()

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
            elif isinstance(spec, TaskSpec):
                self.desired.tasks[spec.name] = spec

    def load_initial_status(self):
        # Load full current state from Executor
        for status in self.executor.list_agents():
            self.store.put_agent(status.name, status)
        for status in self.executor.list_tasks():
            self.store.put_task(status.name, status)

    def _handle_spec_change(self, spec: RosterSpec):
        try:
            if isinstance(spec, AgentSpec):
                self.desired.agents[spec.name] = spec
            elif isinstance(spec, TaskSpec):
                self.desired.tasks[spec.name] = spec
        except KeyError:
            return
        self.reconciliation_queue.put_nowait(True)

    def setup_spec_listeners(self):
        self.roster_informer.add_event_listener(self._handle_spec_change)

    def setup_status_listeners(self):
        self.executor.add_task_status_listener(self._handle_task_status_change)
        self.executor.add_agent_status_listener(self._handle_agent_status_change)

    def _handle_task_status_change(self, event: ExecutorStatusEvent):
        try:
            # Assuming all full updates for Task
            task = event.get_task_status()
            self.store.put_task(event.name, task)
        except ValueError:
            return
        self.reconciliation_queue.put_nowait(True)

    def _handle_agent_status_change(self, event: ExecutorStatusEvent):
        if event.event_type in [EventType.CREATE, EventType.UPDATE]:
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

    def _notify_roster_status_change(self, event: ControllerStatusEvent):
        self.roster_notifier.push_event(event)

    async def reconcile(self):
        # this is for global reconciliation
        # we reconcile sequentially since Tasks depend on Agents
        await self.reconcile_agents()
        await self.reconcile_tasks()

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
        logger.info("Reconciling agents...")
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

    @staticmethod
    def task_matches_spec(task: TaskStatus, spec: TaskSpec):
        return task.name == spec.name and task.agent_name == spec.agent_name

    async def reconcile_tasks(self):
        logger.info("Reconciling tasks...")
        logger.debug("(rec-tasks) Current tasks: %s", self.current.tasks)
        logger.debug("(rec-tasks) Desired tasks: %s", self.desired.tasks)
        for name, spec in self.desired.tasks.items():
            if spec.agent_name not in self.current.agents:
                logger.warn(
                    "(rec-tasks) Agent %s not found, skipping task %s",
                    spec.agent_name,
                    name,
                )
                continue
            if name not in self.current.tasks:
                await self.initiate_task(spec)
            elif not self.task_matches_spec(self.current.tasks[name], spec):
                await self.update_task(spec)
        for name, task in self.current.tasks.items():
            if name not in self.desired.tasks:
                await self.delete_task(task.name)
        logger.debug("(rec-tasks) Final tasks: %s", self.current.tasks)

    async def create_agent(self, agent: AgentSpec) -> AgentStatus:
        if agent.name in self.current.agents:
            raise errors.AgentAlreadyExistsError(agent=agent.name)
        self.store.put_agent(agent.name, await self.executor.create_agent(agent))
        return self.current.agents[agent.name]

    async def update_agent(self, agent: AgentSpec) -> AgentStatus:
        if agent.name not in self.current.agents:
            raise errors.AgentNotFoundError(agent=agent.name)
        self.store.put_agent(agent.name, await self.executor.update_agent(agent))
        return self.current.agents[agent.name]

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
        except errors.AgentNotFoundError:
            pass

        # cascade delete to owned tasks
        current_tasks = list(self.current.tasks.items())
        for task_name, task in current_tasks:
            if task.agent_name != name:
                self.store.delete_task(task.name)

    async def initiate_task(self, task: TaskSpec) -> TaskStatus:
        if task.name in self.current.tasks:
            raise errors.TaskAlreadyExistsError(task=task.name)
        if task.agent_name not in self.current.agents:
            raise errors.AgentNotFoundError(agent=task.agent_name)

        self.store.put_task(task.name, await self.executor.initiate_task(task))
        return self.current.tasks[task.name]

    async def update_task(self, task: TaskSpec) -> TaskStatus:
        if task.name not in self.current.tasks:
            raise errors.TaskNotFoundError(task=task.name)
        if task.agent_name not in self.current.agents:
            raise errors.AgentNotFoundError(agent=task.agent_name)

        self.store.put_task(task.name, await self.executor.update_task(task))
        return self.current.tasks[task.name]

    def list_tasks(self) -> list[TaskStatus]:
        return list(self.current.tasks.values())

    def get_task(self, name: str) -> TaskStatus:
        try:
            return self.current.tasks[name]
        except KeyError as e:
            raise errors.TaskNotFoundError(task=name) from e

    async def delete_task(self, name: str) -> None:
        try:
            await self.executor.end_task(name)
            self.store.delete_task(name)
        except errors.TaskNotFoundError:
            pass
