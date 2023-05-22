import asyncio
import os
import signal
from multiprocessing import Process

import aiohttp
import pytest
from roster_agent_runtime.controllers.agent import AgentController

from tests.mock.executor import MockAgentExecutor
from tests.mock.roster_informer import MockRosterInformer


@pytest.fixture
def process_manager():
    processes = []

    def run_in_process(target, *args, **kwargs):
        proc = Process(target=target, args=args, kwargs=kwargs)
        proc.start()
        processes.append(proc)
        return proc

    yield run_in_process

    for process in processes:
        try:
            if process.is_alive():
                os.kill(process.pid, signal.SIGTERM)
                process.join()
        except Exception:
            print(f"Failed to kill process {process.pid}")


@pytest.fixture
def executor():
    yield MockAgentExecutor()


@pytest.fixture
def roster_informer():
    yield MockRosterInformer()


@pytest.fixture
def controller(executor, roster_informer):
    yield AgentController(
        executor=executor,
        roster_informer=roster_informer,
    )


@pytest.mark.asyncio
async def test_setup_teardown(controller):
    await controller.setup()
    await controller.teardown()


# @pytest.mark.asyncio
# async def test_status_change(controller, executor):
#     await controller.setup()
#     executor.set_agents()
