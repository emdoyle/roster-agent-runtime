from typing import Optional

from pydantic import BaseModel, Field


class ConversationMessage(BaseModel):
    message: str = Field(description="The message.")
    sender: str = Field(description="The sender of the message.")

    class Config:
        validate_assignment = True
        schema_extra = {
            "example": {
                "message": "Hello!",
                "sender": "Alice",
            }
        }


class ConversationSpec(BaseModel):
    agent_name: str = Field(description="The name of the agent.")
    name: str = Field(description="The name of the conversation.")
    context: Optional[dict] = Field(
        default=None, description="The context of the conversation."
    )

    class Config:
        validate_assignment = True
        schema_extra = {
            "example": {
                "agent_name": "Alice",
                "name": "my_conversation",
                "context": {"task": "my_task"},
            }
        }


class ConversationStatus(BaseModel):
    name: str = Field(description="The name of the conversation.")
    status: str = Field(description="The status of the conversation.")
    history: list[ConversationMessage] = Field(
        default_factory=list, description="The conversation history."
    )

    class Config:
        validate_assignment = True
        schema_extra = {
            "example": {
                "name": "my_conversation",
                "status": "in_progress",
                "history": [
                    ConversationMessage.Config.schema_extra["example"],
                ],
            }
        }


class ConversationResource(BaseModel):
    spec: ConversationSpec = Field(description="The specification of the conversation.")
    status: ConversationStatus = Field(description="The status of the conversation.")

    class Config:
        validate_assignment = True
        schema_extra = {
            "example": {
                "spec": ConversationSpec.Config.schema_extra["example"],
                "status": ConversationStatus.Config.schema_extra["example"],
            }
        }
