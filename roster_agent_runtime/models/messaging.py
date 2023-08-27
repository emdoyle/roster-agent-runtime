from typing import Optional

from pydantic import BaseModel, Field


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
