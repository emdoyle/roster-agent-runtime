import asyncio

from roster_agent_runtime.agents.local.handle import LocalAgentHandle

from scripts.util import (
    ROSTER_CODEBASE_TREE_FILE,
    consume_agent_outgoing,
    get_fake_record_id,
)

TEST_DESCRIPTION = """
This project is a Python web service acting as a central API for a system called Roster.
It provides CRUD endpoints for resources which represent configuration for multi-Agent Workflows.
It is also responsible for managing the Roster Runtime on potentially many other machines, primarily through RabbitMQ messaging.
At a high-level, this service uses messages to trigger Actions on Agents, then receives the results of those Actions and advances the state of the associated Workflow as necessary.
"""


async def run_test(record_id: str):
    agent_handle = LocalAgentHandle.build("SoftwareArchitect", "software_architect")
    task = asyncio.create_task(consume_agent_outgoing(agent_handle))
    with open(ROSTER_CODEBASE_TREE_FILE, "r") as f:
        codebase_tree = f.read()
    await agent_handle.trigger_action(
        "Identify",
        "IdentifyDomains",
        {"project_description": TEST_DESCRIPTION, "codebase_tree": codebase_tree},
        "An experienced software architect who specializes in web applications.",
        record_id,
        "ProcessCodebase",
    )
    await task


if __name__ == "__main__":
    record_id = get_fake_record_id()
    print(f"IdentifyDomains: {record_id}")
    asyncio.run(run_test(record_id))
