import asyncio

from roster_agent_runtime.agents.local.handle import LocalAgentHandle

from scripts.util import consume_agent_outgoing, get_fake_record_id

TEST_PLAN = """
<plan>
<modify file="api/identity.py">
* Remove the '{name}' segment from the PATCH route for the update_identity function.
</modify>

<modify file="api/team.py">
* Remove the '{name}' segment from the PATCH route for the update_team function.
</modify>

<modify file="api/workflow.py">
* Remove the '{name}' segment from the PATCH route for the update_workflow function.
</modify>

<modify file="api/agent.py">
* Remove the '{name}' segment from the PATCH route for the update_agent function.
</modify>
</plan>
"""


async def run_test(record_id: str):
    agent_handle = LocalAgentHandle.build("WebDeveloper", "web_developer")
    task = asyncio.create_task(consume_agent_outgoing(agent_handle))

    await agent_handle.trigger_action(
        "WriteCode",
        "WriteCode",
        {"implementation_plan": TEST_PLAN},
        "You are a genius web application engineer with extensive experience in Python.",
        record_id,
        "ImplementFeature",
    )
    await task


if __name__ == "__main__":
    record_id = get_fake_record_id()
    print(f"WriteCode: {record_id}")
    asyncio.run(run_test(record_id))
