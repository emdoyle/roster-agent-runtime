from typing import Callable, Union

from roster_agent_runtime.informers.base import Informer
from roster_agent_runtime.models.agent import AgentSpec
from roster_agent_runtime.models.task import TaskSpec

RosterSpec = Union[AgentSpec, TaskSpec]

# NOTE the specs will break if fields are changed
#   TODO: look into mocking library which can auto-generate mocks

INITIAL_MOCK_DATA = [
    AgentSpec(image="langchain-roster", name="Alice"),
    AgentSpec(image="langchain-roster", name="Bob"),
    TaskSpec(
        agent_name="Alice",
        name="MyTask",
        description="My task description",
    ),
]


class MockRosterInformer(Informer[RosterSpec]):
    def __init__(self):
        self.data = INITIAL_MOCK_DATA
        self.event_listeners = []

    async def setup(self):
        pass

    async def teardown(self):
        pass

    def add_event_listener(self, callback: Callable[[RosterSpec], None]):
        self.event_listeners.append(callback)

    def list(self) -> list[RosterSpec]:
        return self.data

    # Below are methods intended to be used by the test suite
    def set_data(self, data):
        self.data = data

    def get(self, id: str) -> RosterSpec:
        raise NotImplementedError

    def send_event(self, event: RosterSpec):
        for listener in self.event_listeners:
            listener(event)
