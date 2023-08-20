import asyncio

import pytest
import pytest_asyncio
from roster_agent_runtime.controllers.agent import AgentController
from roster_agent_runtime.executors import DockerAgentExecutor
from roster_agent_runtime.informers.roster import RosterInformer
from roster_agent_runtime.models.agent import AgentSpec, AgentStatus


@pytest.fixture
def executor():
    yield DockerAgentExecutor()


@pytest.fixture
def roster_informer():
    yield RosterInformer()


@pytest.fixture
def controller(executor, roster_informer):
    yield AgentController(
        executor=executor,
        roster_informer=roster_informer,
    )


@pytest_asyncio.fixture(autouse=True)
async def manage_controller(controller):
    await controller.setup()
    yield controller
    await controller.teardown()


AGENT_TESTCASES = [
    (
        AgentSpec(image="langchain-roster", name="Alice"),
        AgentStatus(name="Alice", status="running"),
    ),
]


def push_roster_spec(roster_informer: RosterInformer, spec: AgentSpec):
    assert len(roster_informer.event_listeners) > 0
    roster_informer.event_listeners[0](spec)


@pytest.mark.asyncio
async def test_add_spec(controller, roster_informer):
    spec, status = AGENT_TESTCASES[0]
    push_roster_spec(roster_informer, spec)
    await asyncio.sleep(15)
    assert len(controller.list_agents()) == 1
    assert controller.list_agents()[0].name == status.name
    assert controller.list_agents()[0].status == status.status
