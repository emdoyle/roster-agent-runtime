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
