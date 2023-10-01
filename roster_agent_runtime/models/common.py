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

    @classmethod
    def text(cls, name: str):
        return cls(type="text", name=name)

    @classmethod
    def code(cls, name: str):
        return cls(type="code", name=name)


class TypedResult(BaseModel):
    type: str = Field(description="The type of the result.")
    value: str = Field(description="The value of the result.")

    class Config:
        validate_assignment = True
        schema_extra = {
            "example": {
                "type": "text",
                "value": "value",
            }
        }
