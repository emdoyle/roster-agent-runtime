class AgentServiceError(Exception):
    """Base exception class for Agent Service errors."""

    def __init__(self, message="An unexpected error occurred.", details=None):
        super().__init__(message, details)
        self.message = message
        self.details = details


class CreateAgentError(AgentServiceError):
    """Exception raised when an error occurs when creating an Agent."""

    def __init__(
        self,
        message="An error occurred when attempting to create an Agent.",
        details=None,
    ):
        super().__init__(message, details)


class AgentAlreadyExistsError(CreateAgentError):
    """Exception raised when an Agent already exists."""

    def __init__(
        self,
        message="An Agent with the specified name already exists.",
        details=None,
        agent=None,
    ):
        super().__init__(message, details)
        self.agent = agent


class AgentImageNotFoundError(CreateAgentError):
    """Exception raised when an Agent image is not found."""

    def __init__(
        self,
        message="The specified Agent image was not found.",
        details=None,
        image=None,
    ):
        super().__init__(message, details)
        self.image = image


class AgentNotFoundError(AgentServiceError):
    """Exception raised when an Agent is not found."""

    def __init__(
        self, message="The specified Agent was not found.", details=None, agent=None
    ):
        super().__init__(message, details)
        self.agent = agent


class ConversationError(AgentServiceError):
    """Base exception class for Conversation errors."""

    def __init__(
        self,
        message="An unexpected error occurred for the Conversation.",
        details=None,
        conversation=None,
    ):
        super().__init__(message, details)
        self.conversation = conversation


class ConversationAlreadyExistsError(ConversationError):
    """Exception raised when a Conversation already exists."""

    def __init__(
        self,
        message="A Conversation with this ID already exists.",
        details=None,
        conversation=None,
    ):
        super().__init__(message, details, conversation)


class ConversationNotFoundError(ConversationError):
    """Exception raised when a Conversation is not found."""

    def __init__(
        self,
        message="The specified Conversation was not found.",
        details=None,
        conversation=None,
    ):
        super().__init__(message, details, conversation)
