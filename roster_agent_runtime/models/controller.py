from pydantic import BaseModel, Field
from roster_agent_runtime.models.agent import AgentSpec, AgentStatus


class DesiredAgentState(BaseModel):
    agents: dict[str, AgentSpec] = Field(
        description="The list of agents which should be running.",
        default_factory=dict,
    )


class CurrentAgentState(BaseModel):
    agents: dict[str, AgentStatus] = Field(
        description="The list of agents which are currently running.",
        default_factory=dict,
    )
