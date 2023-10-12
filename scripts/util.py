import uuid

from roster_agent_runtime.agents.local.handle import LocalAgentHandle
from roster_agent_runtime.logs import app_logger
from roster_agent_runtime.models.files import FileContents
from roster_agent_runtime.models.messaging import OutgoingMessage

logger = app_logger()
ROSTER_ROOT_DIR = "/Users/evanmdoyle/Programming/roster/roster_api"


async def handle_file_read_message(handle: LocalAgentHandle, message: OutgoingMessage):
    if message.payload.get("tool") != "workspace-file-reader":
        raise ValueError("Unknown tool")
    file_read_inputs = message.payload["data"]["inputs"]
    filepaths = file_read_inputs["filepaths"]
    file_contents = []
    for filepath in filepaths:
        try:
            with open(f"{ROSTER_ROOT_DIR}/{filepath}", "r") as f:
                file_contents.append(FileContents(filename=filepath, text=f.read()))
        except FileNotFoundError:
            await handle.handle_tool_response(
                invocation_id=message.payload["id"],
                tool=message.payload["tool"],
                data={"error": f"File not found: {filepath}"},
            )
            return

    await handle.handle_tool_response(
        invocation_id=message.payload["id"],
        tool=message.payload["tool"],
        data={"files": file_contents},
    )


def handle_action_report_message(message: OutgoingMessage):
    message_data = message.payload["data"]
    if message_data["error"]:
        logger.error(message_data["error"])
    else:
        logger.info(message_data["outputs"])


async def consume_agent_outgoing(handle: LocalAgentHandle):
    async for message in handle.outgoing_message_stream():
        if message.recipient.name == "workspace-manager":
            # unsafe assumption in the future but assume this is file read tool use
            await handle_file_read_message(handle, message)
        elif message.recipient.name == "workflow-router":
            # unsafe assumption in the future but assume this is action report
            handle_action_report_message(message)
            return
        else:
            logger.warning("unknown message: %s", message)
            return


def get_fake_record_id() -> str:
    return f"fake-record-{uuid.uuid4()}"
