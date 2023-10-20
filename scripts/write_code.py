import asyncio

from roster_agent_runtime.agents.local.handle import LocalAgentHandle

from scripts.util import (
    ROSTER_CODEBASE_SUMMARY_FILE,
    ROSTER_CODEBASE_TREE_FILE,
    ROSTER_EXTENDED_EXPERTS_FILE,
    consume_agent_outgoing,
    get_fake_record_id,
)

CHANGE_REQUEST = """
When the ImplementFeature Workflow is completed, right now the WorkspaceManager coordinates submitting a Pull Request including the changes.
I want to add a link to the resulting Pull Request in a comment on the original GitHub Issue which triggered the workflow.
"""

EXPERT_INSTRUCTIONS = """<plan>
<expert name="Workspace Expert">
<instructions>
Modify the code that handles the creation of a Pull Request. After the PR is successfully created, trigger a new event (e.g., `PullRequestCreatedEvent`) that includes the necessary information to find the original issue and the link to the PR.
</instructions>
</expert>
<expert name="Github Integration Expert">
<instructions>
Add a new handler for the `PullRequestCreatedEvent`. This handler should find the original issue (using the information provided in the event) and add a comment with the link to the PR.
</instructions>
<dependency name="Workspace Expert">
Your work depends on the Workspace Expert. You will need to wait until the `PullRequestCreatedEvent` is being triggered correctly before you can handle it.
</dependency>
</expert>
</plan>"""
#
# CHANGE_REQUEST = """
# The RosterGithubApp shouldn't be responsible for handling the workflow finish event. Instead, the Workspace Manager should listen for this event directly.
# There is no need for the Workspace Manager to receive a code report message via RMQ once this change is made.
# """
#
#
# EXPERT_INSTRUCTIONS = """<plan>
# <expert name="Github Integration Expert">
# <instructions>
# Modify the `github/app.py` file to stop the RosterGithubApp from sending a code report message via RabbitMQ when it receives a workflow finish event. Ensure that the RosterGithubApp still processes the workflow finish event correctly, but it should no longer send a message to the Workspace Manager.
# </instructions>
# </expert>
# <expert name="Workspace Expert">
# <instructions>
# Modify the `workspace/manager.py` file to make the Workspace Manager listen for the workflow finish event directly. This will involve setting up a new event listener for the WorkflowFinishEvent. When the Workspace Manager receives this event, it should process the event in the same way as it previously processed the code report message from the RosterGithubApp.
# </instructions>
# <dependency name="Github Integration Expert">
# The changes in the Workspace Manager depend on the changes in the RosterGithubApp. The Workspace Manager should start listening for the workflow finish event directly only after the RosterGithubApp has stopped sending the code report message via RabbitMQ.
# </dependency>
# </expert>
# </plan>"""


async def run_test(record_id: str):
    agent_handle = LocalAgentHandle.build("WebDeveloper", "web_developer")
    task = asyncio.create_task(consume_agent_outgoing(agent_handle))
    change_request = CHANGE_REQUEST
    expert_instructions = EXPERT_INSTRUCTIONS
    with open(ROSTER_CODEBASE_TREE_FILE, "r") as f:
        codebase_tree = f.read()
    with open(ROSTER_CODEBASE_SUMMARY_FILE, "r") as f:
        project_summary = f.read()
    with open(ROSTER_EXTENDED_EXPERTS_FILE, "r") as f:
        experts = f.read()

    await agent_handle.trigger_action(
        "WriteCode",
        "WriteCode",
        {
            "change_request": change_request,
            "project_summary": project_summary,
            "codebase_tree": codebase_tree,
            "experts": experts,
            "expert_instructions": expert_instructions,
        },
        "You are a genius web application engineer with extensive experience in Python.",
        record_id,
        "ImplementFeature",
    )
    await task


if __name__ == "__main__":
    record_id = get_fake_record_id()
    print(f"WriteCode: {record_id}")
    asyncio.run(run_test(record_id))
