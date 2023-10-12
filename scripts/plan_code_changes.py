import asyncio
import os

from roster_agent_runtime.agents.local.handle import LocalAgentHandle
from roster_agent_runtime.logs import app_logger

from scripts.util import consume_agent_outgoing, get_fake_record_id

logger = app_logger()

script_dir = os.path.dirname(os.path.abspath(__file__))
ROSTER_CODEBASE_TREE_FILE = os.path.join(script_dir, "roster_codebase_tree.txt")

CHANGE_REQUEST = (
    """Remove the 'name' parameter from the patch endpoints for all resource types."""
)


async def run_test(record_id: str):
    agent_handle = LocalAgentHandle.build("WebDeveloper", "web_developer")
    task = asyncio.create_task(consume_agent_outgoing(agent_handle))

    change_request = CHANGE_REQUEST
    with open(ROSTER_CODEBASE_TREE_FILE, "r") as f:
        codebase_tree = f.read()
    await agent_handle.trigger_action(
        "PlanCode",
        "PlanCodeChanges",
        {"change_request": change_request, "codebase_tree": codebase_tree},
        "You are a genius web application engineer with extensive experience in Python.",
        record_id,
        "ImplementFeature",
    )
    await task


if __name__ == "__main__":
    record_id = get_fake_record_id()
    print(f"PlanCodeChanges: {record_id}")
    asyncio.run(run_test(record_id))
