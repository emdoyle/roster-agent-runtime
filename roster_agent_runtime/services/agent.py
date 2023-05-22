# class AgentService:
#     async def start_conversation(
#         self, conversation: ConversationSpec
#     ) -> ConversationStatus:
#         if conversation.name in self.conversations:
#             raise errors.ConversationAlreadyExistsError(conversation=conversation.name)
#         if conversation.agent_name not in self.agents:
#             raise errors.AgentNotFoundError(agent=conversation.agent_name)
#
#         conversation_status = ConversationStatus(status="running")
#         self.conversations[conversation.name] = ConversationResource(
#             spec=conversation, status=conversation_status
#         )
#         return conversation_status
#
#     async def prompt(
#         self, name: str, conversation_message: ConversationMessage
#     ) -> ConversationMessage:
#         try:
#             conversation_spec = self.state.desired.conversations[name]
#             conversation_status = self.state.current.conversations[name]
#         except KeyError as e:
#             raise errors.ConversationNotFoundError(conversation=name) from e
#         if conversation.spec.agent_name not in self.agents:
#             raise errors.AgentNotFoundError(agent=conversation.spec.agent_name)
#         if conversation.status != "running":
#             raise errors.ConversationNotAvailableError(conversation=name)
#
#         return await self.executor.prompt(conversation, conversation_message)
#
#     async def end_conversation(self, name: str) -> None:
#         try:
#             conversation = self.state.current.conversations.pop(name)
#         except KeyError as e:
#             raise errors.ConversationNotFoundError(conversation=name) from e
#         if conversation.status != "running":
#             raise errors.ConversationNotAvailableError(conversation=name)
