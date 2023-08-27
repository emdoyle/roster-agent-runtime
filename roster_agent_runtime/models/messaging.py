from typing import Optional

from pydantic import BaseModel, Field


class WorkflowActionTriggerPayload(BaseModel):
    action: str = Field(
        description="The name of the Action reporting outputs in this payload."
    )
    inputs: dict[str, str] = Field(
        description="The inputs for the Action being triggered."
    )

    class Config:
        validate_assignment = True
        schema_extra = {
            "example": {
                "action": "ActionName",
                "inputs": {"input1": "value1", "input2": "value2"},
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
        action: str,
        outputs: Optional[dict] = None,
        error: str = "",
    ):
        return cls(
            recipient=Recipient.workflow_router(),
            payload={
                "id": record_id,
                "workflow": workflow,
                "kind": "report_action",
                "payload": {"action": action, "outputs": outputs, "error": error},
            },
        )
