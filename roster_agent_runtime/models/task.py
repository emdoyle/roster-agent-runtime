from typing import Optional

from pydantic import BaseModel, Field


class TaskSpec(BaseModel):
    name: str = Field(description="A name to identify the task.")
    description: str = Field(description="A description of the task.")
    assignment_affinities: Optional[list[str]] = Field(
        default=None, description="A list of assignment affinities for the task."
    )
    assignment_anti_affinities: Optional[list[str]] = Field(
        default=None, description="A list of assignment anti-affinities for the task."
    )

    class Config:
        validate_assignment = True
        schema_extra = {
            "example": {
                "name": "my_task",
                "description": "my task",
                "assignment_affinities": ["software engineer", "backend"],
                "assignment_anti_affinities": ["frontend"],
            }
        }


class TaskAssignment(BaseModel):
    team_name: str = Field(description="The name of the team.")
    role_name: str = Field(description="The name of the role.")
    agent_name: str = Field(description="The name of the agent.")

    class Config:
        validate_assignment = True
        schema_extra = {
            "example": {
                "team_name": "my_team",
                "role_name": "my_role",
                "agent_name": "my_agent",
            }
        }


class TaskStatus(BaseModel):
    name: str = Field(description="The name of the task.")
    status: str = Field(default="pending", description="The status of the task.")
    assignment: Optional[TaskAssignment] = Field(
        default=None, description="Who is assigned to the task."
    )

    class Config:
        validate_assignment = True
        schema_extra = {
            "example": {
                "name": "my_task",
                "status": "running",
                "assignment": TaskAssignment.Config.schema_extra["example"],
            }
        }


class InitiateTaskArgs(BaseModel):
    task: str = Field(description="The name of the task.")
    description: str = Field(description="The description of the task.")
    assignment: Optional[TaskAssignment] = Field(
        default=None, description="Who is assigned to the task."
    )

    class Config:
        validate_assignment = True
        schema_extra = {
            "example": {
                "name": "my_task",
                "description": "my task",
                "assignment": TaskAssignment.Config.schema_extra["example"],
            }
        }
