class RosterError(Exception):
    """Base exception class for Agent Service errors."""

    def __init__(self, message="An unexpected error occurred.", details=None):
        super().__init__(message, details)
        self.message = message
        self.details = details


class AgentError(RosterError):
    """Exception raised for agent-related errors."""

    def __init__(
        self,
        message="An unexpected error occurred for the Agent.",
        details=None,
        agent=None,
    ):
        super().__init__(message, details)
        self.agent = agent


class CreateAgentError(AgentError):
    """Exception raised when an error occurs when creating an Agent."""

    def __init__(
        self,
        message="An error occurred when attempting to create an Agent.",
        details=None,
        agent=None,
    ):
        super().__init__(message, details)
        self.agent = agent


class AgentFailedToStartError(AgentError):
    """Exception raised when an Agent fails to start."""

    def __init__(
        self,
        message="The Agent failed to start.",
        details=None,
        agent=None,
    ):
        super().__init__(message, details)
        self.agent = agent


class AgentAlreadyExistsError(AgentError):
    """Exception raised when an Agent already exists."""

    def __init__(
        self,
        message="An Agent with the specified name already exists.",
        details=None,
        agent=None,
    ):
        super().__init__(message, details)
        self.agent = agent


class AgentImageNotFoundError(AgentError):
    """Exception raised when an Agent image is not found."""

    def __init__(
        self,
        message="The specified Agent image was not found.",
        details=None,
        image=None,
    ):
        super().__init__(message, details)
        self.image = image


class AgentNotFoundError(AgentError):
    """Exception raised when an Agent is not found."""

    def __init__(
        self, message="The specified Agent was not found.", details=None, agent=None
    ):
        super().__init__(message, details)
        self.agent = agent


class InvalidRequestError(RosterError):
    """Exception raised when an invalid request is made."""

    def __init__(
        self,
        message="The request is invalid.",
        details=None,
    ):
        super().__init__(message, details)


class SetupError(RosterError):
    """Exception raised when an error occurs during set up."""

    def __init__(
        self,
        message="An error occurred when attempting to set up.",
        details=None,
    ):
        super().__init__(message, details)


class TeardownError(RosterError):
    """Exception raised when an error occurs during tear down."""

    def __init__(
        self,
        message="An error occurred when attempting to tear down.",
        details=None,
    ):
        super().__init__(message, details)


class InvalidEventError(RosterError):
    """Exception raised when an invalid event is received."""

    def __init__(
        self,
        message="The event is invalid.",
        details=None,
    ):
        super().__init__(message, details)
