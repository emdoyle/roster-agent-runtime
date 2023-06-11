from pydantic import BaseModel, Field

from ..conversation import ConversationMessage


class ChatPromptAgentArgs(BaseModel):
    history: list[ConversationMessage] = Field(
        description="The history of the conversation."
    )
    message: ConversationMessage = Field(
        description="The message to send to the agent."
    )
    team: str = Field(
        description="The name of the team, which the agent will use as context for the conversation.",
        default="",
    )

    class Config:
        validate_assignment = True
        schema_extra = {
            "example": {
                "history": [ConversationMessage.Config.schema_extra["example"]],
                "message": ConversationMessage.Config.schema_extra["example"],
                "team": "my_team",
            }
        }
