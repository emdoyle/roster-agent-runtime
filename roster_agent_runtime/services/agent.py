from roster_agent_runtime.executors import AgentExecutor
from roster_agent_runtime.models.conversation import ConversationMessage


class AgentService:
    def __init__(self, executor: AgentExecutor):
        self.executor = executor

    async def chat_prompt_agent(
        self,
        name: str,
        history: list[ConversationMessage],
        message: ConversationMessage,
    ) -> ConversationMessage:
        return await self.executor.prompt(name, history, message)
