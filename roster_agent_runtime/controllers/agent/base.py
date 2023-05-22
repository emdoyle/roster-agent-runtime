import asyncio
from typing import Optional

from roster_agent_runtime.controllers.agent import errors
from roster_agent_runtime.executors import AgentExecutor
from roster_agent_runtime.informers.roster import RosterInformer, RosterSpec
from roster_agent_runtime.models.agent import AgentSpec, AgentStatus
from roster_agent_runtime.models.controller import ControllerState
from roster_agent_runtime.models.task import TaskSpec, TaskStatus

AGENT_CONTROLLER: Optional["AgentController"] = None


def get_agent_controller() -> "AgentController":
    global AGENT_CONTROLLER
    if AGENT_CONTROLLER is not None:
        return AGENT_CONTROLLER

    # This should be configurable in settings
    from roster_agent_runtime.executors.docker import DockerAgentExecutor

    AGENT_CONTROLLER = AgentController(
        executor=DockerAgentExecutor(), roster_informer=RosterInformer()
    )
    return AGENT_CONTROLLER


# TODO: fix thread/coroutine safety throughout

# Consider separating TaskController from AgentController
# main thing is the Executor relationship
class AgentController:
    def __init__(self, executor: AgentExecutor, roster_informer: RosterInformer):
        # TODO: properly abstract executor per-Agent
        self.executor = executor
        self.roster_informer = roster_informer
        self.state = ControllerState()

    @property
    def desired(self):
        return self.state.desired

    @property
    def current(self):
        return self.state.current

    async def setup(self):
        try:
            await asyncio.gather(
                self.setup_roster_connection(), self.setup_executor_connection()
            )
            print("Connections established.\nReconciling...")
            await self.reconcile()
            print("Reconciled.")
        except Exception as e:
            await self.teardown()
            raise errors.SetupError from e

    async def teardown(self):
        try:
            await asyncio.gather(
                self.roster_informer.teardown(), self.executor.teardown()
            )
        except Exception as e:
            raise errors.TeardownError from e

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
            self.current.agents[status.name] = status
        for status in self.executor.list_tasks():
            self.current.tasks[status.name] = status

    def _handle_spec_change(self, spec: RosterSpec):
        try:
            if isinstance(spec, AgentSpec):
                self.desired.agents[spec.name] = spec
            elif isinstance(spec, TaskSpec):
                self.desired.tasks[spec.name] = spec
        except KeyError:
            pass

    def setup_spec_listeners(self):
        self.roster_informer.add_event_listener(self._handle_spec_change)

    def setup_status_listeners(self):
        self.executor.add_task_status_listener(self._handle_task_status_change)
        self.executor.add_agent_status_listener(self._handle_agent_status_change)

    def _handle_task_status_change(self, task: TaskStatus):
        try:
            self.state.current.tasks[task.name] = task
        except KeyError:
            pass

    def _handle_agent_status_change(self, agent: AgentStatus):
        try:
            self.state.current.agents[agent.name] = agent
        except KeyError:
            pass

    async def reconcile(self):
        # naive algorithm,
        # but simply reconcile sequentially since Tasks depend on Agents
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
        print("Reconciling agents...")
        print("Current agents:", self.current.agents)
        print("Desired agents:", self.desired.agents)
        updated_agents = {}
        for name, spec in self.desired.agents.items():
            if name not in self.current.agents:
                await self.create_agent(spec)
            elif not self.agent_matches_spec(self.current.agents[name], spec):
                await self.update_agent(spec)
            updated_agents[name] = spec
        current_agents = list(self.current.agents.items())
        for name, agent in current_agents:
            if name not in updated_agents:
                await self.delete_agent(agent.name)
        self.current.agents = updated_agents

    @staticmethod
    def task_matches_spec(task: TaskStatus, spec: TaskSpec):
        return task.name == spec.name and task.agent_name == spec.agent_name

    async def reconcile_tasks(self):
        updated_tasks = {}
        for name, spec in self.desired.tasks.items():
            if spec.agent_name not in self.current.agents:
                # spec is invalid, or we haven't reconciled agents -> skip
                # should also log warning
                continue
            if name not in self.current.tasks:
                await self.initiate_task(spec)
            elif not self.task_matches_spec(self.current.tasks[name], spec):
                await self.update_task(spec)
            updated_tasks[name] = spec
        for name, task in self.current.tasks.items():
            if name not in updated_tasks:
                await self.delete_task(task.name)
        self.current.tasks = updated_tasks

    async def create_agent(self, agent: AgentSpec) -> AgentStatus:
        if agent.name in self.current.agents:
            raise errors.AgentAlreadyExistsError(agent=agent.name)
        self.current.agents[agent.name] = await self.executor.create_agent(agent)
        return self.current.agents[agent.name]

    async def update_agent(self, agent: AgentSpec) -> AgentStatus:
        if agent.name not in self.current.agents:
            raise errors.AgentNotFoundError(agent=agent.name)
        self.current.agents[agent.name] = await self.executor.update_agent(agent)
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
            self.current.agents.pop(name)
            self.current.tasks = {
                task_name: task
                for task_name, task in self.current.tasks.items()
                if task.agent_name != name
            }
        except KeyError as e:
            raise errors.AgentNotFoundError(agent=name) from e

        return await self.executor.delete_agent(name)

    async def initiate_task(self, task: TaskSpec) -> TaskStatus:
        if task.name in self.current.tasks:
            raise errors.TaskAlreadyExistsError(task=task.name)
        if task.agent_name not in self.current.agents:
            raise errors.AgentNotFoundError(agent=task.agent_name)

        self.current.tasks[task.name] = await self.executor.initiate_task(task)
        return self.current.tasks[task.name]

    async def update_task(self, task: TaskSpec) -> TaskStatus:
        if task.name not in self.current.tasks:
            raise errors.TaskNotFoundError(task=task.name)
        if task.agent_name not in self.current.agents:
            raise errors.AgentNotFoundError(agent=task.agent_name)

        self.current.tasks[task.name] = await self.executor.update_task(task)
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
            self.current.tasks.pop(name)
        except KeyError as e:
            raise errors.TaskNotFoundError(task=name) from e

        return await self.executor.end_task(name)
