from roster_agent_runtime.agents import AgentHandle
from roster_agent_runtime.executors import AgentExecutor
from roster_agent_runtime.models.conversation import ConversationMessage


class AgentService:
    def __init__(self, executor: AgentExecutor):
        self.executor = executor

    def _get_agent_handle(self, name: str) -> AgentHandle:
        return self.executor.get_agent_handle(name)

    async def chat_prompt_agent(
        self,
        name: str,
        identity: str,
        team: str,
        role: str,
        history: list[ConversationMessage],
        message: ConversationMessage,
        execution_id: str = "",
        execution_type: str = "",
    ) -> str:
        agent = self._get_agent_handle(name)
        return await agent.chat(
            identity=identity,
            team=team,
            role=role,
            chat_history=[*history, message],
            execution_id=execution_id,
            execution_type=execution_type,
        )
