from pydantic import BaseModel, Field
from roster_agent_runtime.models.agent import AgentSpec, AgentStatus
from roster_agent_runtime.models.conversation import (
    ConversationSpec,
    ConversationStatus,
)
from roster_agent_runtime.models.task import TaskSpec, TaskStatus


class DesiredState(BaseModel):
    agents: dict[str, AgentSpec] = Field(
        description="The list of agents which should be running.",
        default_factory=dict,
    )
    tasks: dict[str, TaskSpec] = Field(
        description="The list of tasks which should be running.",
        default_factory=dict,
    )
    conversations: dict[str, ConversationSpec] = Field(
        description="The list of conversations which should be active.",
        default_factory=dict,
    )


class CurrentState(BaseModel):
    agents: dict[str, AgentStatus] = Field(
        description="The list of agents which are currently running.",
        default_factory=dict,
    )
    tasks: dict[str, TaskStatus] = Field(
        description="The list of tasks which are currently running.",
        default_factory=dict,
    )
    conversations: dict[str, ConversationStatus] = Field(
        description="The list of conversations which are currently active.",
        default_factory=dict,
    )


class ControllerState(BaseModel):
    desired: DesiredState = Field(
        description="The desired state of the controller's resources.",
        default_factory=DesiredState,
    )
    current: CurrentState = Field(
        description="The current state of the controller's resources.",
        default_factory=CurrentState,
    )
