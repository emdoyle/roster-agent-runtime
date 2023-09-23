from typing import Optional

from pydantic import BaseModel, Field
from roster_agent_runtime.models.common import TypedArgument
from roster_agent_runtime.models.files import FileContents


class WorkflowActionTriggerPayload(BaseModel):
    step: str = Field(
        description="The name of the Step reporting outputs in this payload."
    )
    action: str = Field(description="The name of the Action being triggered.")
    inputs: dict[str, str] = Field(
        description="The inputs for the Action being triggered."
    )
    role_context: str = Field(
        description="A description of the Role which is performing the Action."
    )

    class Config:
        validate_assignment = True
        schema_extra = {
            "example": {
                "step": "StepName",
                "action": "ActionName",
                "inputs": {"input1": "value1", "input2": "value2"},
                "role_context": "A description of the role",
            }
        }


class WorkflowMessage(BaseModel):
    id: str = Field(
        description="An identifier for the workflow record this message refers to."
    )
    workflow: str = Field(description="The workflow this message refers to.")
    kind: str = Field(description="The kind of the message data.")
    data: dict = Field(default_factory=dict, description="The data of the message.")

    class Config:
        validate_assignment = True
        schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "workflow": "WorkflowName",
                "kind": "initiate_workflow",
                "data": {
                    "inputs": {"input1": "value1", "input2": "value2"},
                },
            }
        }


class ReadFileResponsePayload(BaseModel):
    files: list[FileContents] = Field(
        default_factory=list,
        description="The file contents which were requested from the workspace tool.",
    )

    class Config:
        validate_assignment = True
        schema_extra = {
            "example": {
                "files": [
                    FileContents.Config.schema_extra["example"],
                    FileContents.Config.schema_extra["example"],
                ]
            }
        }


class ToolMessage(BaseModel):
    id: str = Field(description="An identifier for this tool invocation.")
    kind: str = Field(description="The kind of the message data.")
    tool: str = Field(description="The tool which this message refers to.")
    data: dict = Field(default_factory=dict, description="The data of the message.")
    error: str = Field(
        default="",
        description="An error message returned by the tool, if any.",
    )

    class Config:
        validate_assignment = True
        schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "tool": "ToolName",
                "kind": "tool_response",
                "data": {
                    "outputs": {"output1": "value1", "output2": "value2"},
                },
                "error": "",
            }
        }


class Recipient(BaseModel):
    kind: str = Field(
        description="The kind of recipient (agent, roster-admin, tool etc.)"
    )
    name: str = Field(description="The name of the recipient")
    namespace: str = Field(
        default="default", description="The namespace of the recipient"
    )

    class Config:
        validate_assignment = True
        schema_extra = {
            "example": {
                "kind": "roster-admin",
                "name": "workflow-router",
                "namespace": "default",
            }
        }

    @classmethod
    def workflow_router(cls, namespace: str = "default") -> "Recipient":
        return cls(kind="roster-admin", name="workflow-router", namespace=namespace)

    @classmethod
    def workspace_manager(cls, namespace: str = "default") -> "Recipient":
        return cls(kind="roster-admin", name="workspace-manager", namespace=namespace)


class OutgoingMessage(BaseModel):
    recipient: Recipient = Field(
        description="The recipient addressing information for the message"
    )
    payload: dict = Field(description="The payload of the message")

    class Config:
        validate_assignment = True
        schema_extra = {
            "example": {
                "recipient": Recipient.Config.schema_extra["example"],
                "payload": {"key": "value"},
            }
        }

    @classmethod
    def workflow_action_result(
        cls,
        record_id: str,
        workflow: str,
        step: str,
        action: str,
        outputs: Optional[dict[str, str]] = None,
        output_types: Optional[tuple[TypedArgument, ...]] = None,
        error: str = "",
    ):
        return cls(
            recipient=Recipient.workflow_router(),
            payload={
                "id": record_id,
                "workflow": workflow,
                "kind": "report_action",
                "data": {
                    "step": step,
                    "action": action,
                    "outputs": outputs,
                    "output_types": output_types,
                    "error": error,
                },
            },
        )

    # TODO: name/namespace Sender info should be added throughout the messaging system
    @classmethod
    def tool_invocation(
        cls,
        invocation_id: str,
        tool: str,
        inputs: dict,
        name: str,
        namespace: str = "default",
    ):
        return cls(
            recipient=Recipient.workspace_manager(),
            payload={
                "id": invocation_id,
                "tool": tool,
                "kind": "tool_invocation",
                "sender": {"name": name, "namespace": namespace},
                "data": {
                    "inputs": inputs,
                },
            },
        )
