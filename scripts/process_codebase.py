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

TEST_EXPERTS = """<expert name="API Expert">
<description>
This expert is responsible for the API endpoints of the Roster system. They will manage the creation, retrieval, updating, and deletion of agents and workflows.
</description>
<entity dir="api" />
<entity file="api/agent.py" />
<entity file="api/workflow.py" />
</expert>

<expert name="Database Expert">
<description>
This expert is responsible for the database connections and setup for the Roster system. They will manage the data persistence layer for the system.
</description>
<entity dir="db" />
</expert>

<expert name="Messaging Expert">
<description>
This expert is responsible for the messaging system of the Roster system. They will manage the RabbitMQ client and the routing of workflow messages.
</description>
<entity file="messaging/rabbitmq.py" />
<entity file="messaging/workflow.py" />
</expert>

<expert name="Data Models Expert">
<description>
This expert is responsible for the data models of the Roster system. They will manage the data structures used throughout the system.
</description>
<entity dir="models" />
</expert>

<expert name="Services Expert">
<description>
This expert is responsible for the service classes of the Roster system. They will manage the business logic for handling agents, workflows, identities, and teams.
</description>
<entity dir="services" />
</expert>

<expert name="System Configuration Expert">
<description>
This expert is responsible for the configuration settings of the Roster system. They will manage the customization of the system's behavior.
</description>
<entity file="settings.py" />
</expert>

<expert name="Watchers Expert">
<description>
This expert is responsible for the watcher classes of the Roster system. They will manage the monitoring of changes in resources and triggering appropriate actions.
</description>
<entity dir="watchers" />
</expert>

<expert name="System Initialization Expert">
<description>
This expert is responsible for the main entry point of the Roster system. They will manage the setup and start of the system.
</description>
<entity file="main.py" />
</expert>"""


async def run_test(record_id: str):
    agent_handle = LocalAgentHandle.build("SoftwareArchitect", "software_architect")
    task = asyncio.create_task(consume_agent_outgoing(agent_handle))
    with open(ROSTER_CODEBASE_TREE_FILE, "r") as f:
        codebase_tree = f.read()
    # await agent_handle.trigger_action(
    #     "Experts",
    #     "SuggestExperts",
    #     {"project_description": TEST_DESCRIPTION, "codebase_tree": codebase_tree},
    #     "An experienced software architect who specializes in web applications.",
    #     record_id,
    #     "ProcessCodebase",
    # )
    await agent_handle.trigger_action(
        "Summarize",
        "SummarizeCodebase",
        {
            "project_description": TEST_DESCRIPTION,
            "codebase_tree": codebase_tree,
            "experts": TEST_EXPERTS,
        },
        "An experienced software architect who specializes in web applications.",
        record_id,
        "ProcessCodebase",
    )
    await task


if __name__ == "__main__":
    record_id = get_fake_record_id()
    print(f"SuggestExperts: {record_id}")
    asyncio.run(run_test(record_id))
