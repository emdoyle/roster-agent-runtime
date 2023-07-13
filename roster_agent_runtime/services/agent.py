from roster_agent_runtime.agents import AgentHandle
from roster_agent_runtime.executors import AgentExecutor
from roster_agent_runtime.models.conversation import ConversationMessage
from roster_agent_runtime.models.task import TaskAssignment


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

    async def initiate_task_on_agent(
        self, name: str, task: str, description: str, assignment: TaskAssignment
    ):
        agent = self._get_agent_handle(name)
        await agent.execute_task(task, description, assignment)

    async def update_task_on_agent(self, name: str, task: str, description: str):
        agent = self._get_agent_handle(name)
        await agent.update_task(task, description)

    async def list_tasks_on_agent(self, name: str):
        agent = self._get_agent_handle(name)
        return await agent.list_tasks()

    async def get_task_on_agent(self, name: str, task: str):
        agent = self._get_agent_handle(name)
        return await agent.get_task(task)

    async def cancel_task_on_agent(self, name: str, task: str):
        agent = self._get_agent_handle(name)
        await agent.cancel_task(task)
