import asyncio

from roster_agent_runtime.agents.local.handle import LocalAgentHandle
from roster_agent_runtime.logs import app_logger

from scripts.util import (
    ROSTER_CODEBASE_SUMMARY_FILE,
    ROSTER_CODEBASE_TREE_FILE,
    ROSTER_EXPERT_SUMMARIES_FILE,
    consume_agent_outgoing,
    get_fake_record_id,
)

logger = app_logger()

CHANGE_REQUEST = """
When the ImplementFeature Workflow is completed, right now the WorkspaceManager coordinates submitting a Pull Request including the changes.
I want to add a link to the resulting Pull Request in a comment on the original GitHub Issue which triggered the workflow.
"""


async def run_test(record_id: str):
    agent_handle = LocalAgentHandle.build("WebDeveloper", "web_developer")
    task = asyncio.create_task(consume_agent_outgoing(agent_handle))

    change_request = CHANGE_REQUEST
    with open(ROSTER_CODEBASE_TREE_FILE, "r") as f:
        codebase_tree = f.read()
    with open(ROSTER_CODEBASE_SUMMARY_FILE, "r") as f:
        project_summary = f.read()
    with open(ROSTER_EXPERT_SUMMARIES_FILE, "r") as f:
        expert_summaries = f.read()

    await agent_handle.trigger_action(
        "PlanCode",
        "PlanCodeChanges",
        {
            "project_summary": project_summary,
            "expert_summaries": expert_summaries,
            "change_request": change_request,
            "codebase_tree": codebase_tree,
        },
        "You are a genius web application engineer with extensive experience in Python.",
        record_id,
        "ImplementFeature",
    )
    await task


if __name__ == "__main__":
    record_id = get_fake_record_id()
    print(f"PlanCodeChanges: {record_id}")
    asyncio.run(run_test(record_id))
