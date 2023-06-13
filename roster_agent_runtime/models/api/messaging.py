from pydantic import BaseModel, Field

from ..conversation import ConversationMessage


class ChatPromptAgentArgs(BaseModel):
    team: str = Field(description="The name of the team which the agent is on.")
    role: str = Field(
        description="The name of the role on the team which identifies the agent."
    )
    history: list[ConversationMessage] = Field(
        description="The history of the conversation."
    )
    message: ConversationMessage = Field(
        description="The message to send to the agent."
    )

    class Config:
        validate_assignment = True
        schema_extra = {
            "example": {
                "team": "my_team",
                "role": "my_role",
                "history": [ConversationMessage.Config.schema_extra["example"]],
                "message": ConversationMessage.Config.schema_extra["example"],
            }
        }
