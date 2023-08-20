from pydantic import BaseModel, Field


class TypedArgument(BaseModel):
    name: str = Field(description="The name of the argument.")
    type: str = Field(description="The type of the argument.")

    class Config:
        validate_assignment = True
        schema_extra = {
            "example": {
                "name": "ArgumentName",
                "type": "ArgumentType",
            }
        }
