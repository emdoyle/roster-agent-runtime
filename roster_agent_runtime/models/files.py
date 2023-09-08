from pydantic import BaseModel, Field


class FileContents(BaseModel):
    filename: str
    text: str
    metadata: dict = Field(default_factory=dict)

    class Config:
        validate_assignment = True
        schema_extra = {
            "example": {
                "filename": "myfile.py",
                "text": "print('hello, world')",
                "metadata": {"latest_hash": "lkuasdf"},
            }
        }
