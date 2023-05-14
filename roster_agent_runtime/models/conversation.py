from typing import Optional

from pydantic import BaseModel, Field

from .agent import AgentContainer


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


class ConversationResource(BaseModel):
    agent_name: str = Field(description="The name of the agent.")
    history: list[ConversationMessage] = Field(
        default_factory=list, description="The conversation history."
    )
    id: str = Field(description="The id of the conversation.")
    name: str = Field(description="The name of the conversation.")
    status: str = Field(description="The status of the conversation.")
    container: Optional[AgentContainer] = Field(
        default=None,
        description="The running container of the agent holding the conversation.",
    )

    class Config:
        validate_assignment = True
        schema_extra = {
            "example": {
                "agent_name": "Alice",
                "history": [
                    ConversationMessage.Config.schema_extra["example"],
                ],
                "id": "my_conversation_id",
                "name": "my_conversation",
                "status": "in_progress",
                "container": AgentContainer.Config.schema_extra["example"],
            }
        }
