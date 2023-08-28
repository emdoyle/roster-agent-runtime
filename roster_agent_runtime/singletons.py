from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from roster_agent_runtime.agents.pool import AgentPool
    from roster_agent_runtime.controllers.agent import AgentController
    from roster_agent_runtime.informers.roster import RosterInformer
    from roster_agent_runtime.messaging.rabbitmq import RabbitMQClient
    from roster_agent_runtime.messaging.router import MessageRouter
    from roster_agent_runtime.notifier import RosterNotifier
    from roster_agent_runtime.services.agent import AgentService

ROSTER_INFORMER: Optional["RosterInformer"] = None
ROSTER_NOTIFIER: Optional["RosterNotifier"] = None
AGENT_POOL: Optional["AgentPool"] = None
AGENT_CONTROLLER: Optional["AgentController"] = None
AGENT_SERVICE: Optional["AgentService"] = None
RABBITMQ_CLIENT: Optional["RabbitMQClient"] = None
MESSAGE_ROUTER: Optional["MessageRouter"] = None


def get_roster_informer() -> "RosterInformer":
    global ROSTER_INFORMER
    if ROSTER_INFORMER is not None:
        return ROSTER_INFORMER

    from roster_agent_runtime.informers.roster import RosterInformer

    ROSTER_INFORMER = RosterInformer()
    return ROSTER_INFORMER


def get_roster_notifier() -> "RosterNotifier":
    global ROSTER_NOTIFIER
    if ROSTER_NOTIFIER is not None:
        return ROSTER_NOTIFIER

    from roster_agent_runtime.notifier import RosterNotifier

    ROSTER_NOTIFIER = RosterNotifier()
    return ROSTER_NOTIFIER


def get_agent_pool() -> "AgentPool":
    global AGENT_POOL
    if AGENT_POOL is not None:
        return AGENT_POOL

    from roster_agent_runtime.agents.pool import AgentPool

    # TODO: Make this configurable
    from roster_agent_runtime.executors.docker import DockerAgentExecutor

    AGENT_POOL = AgentPool(executors=[DockerAgentExecutor()])

    return AGENT_POOL


def get_agent_controller() -> "AgentController":
    global AGENT_CONTROLLER
    if AGENT_CONTROLLER is not None:
        return AGENT_CONTROLLER

    from roster_agent_runtime.controllers.agent import AgentController

    AGENT_CONTROLLER = AgentController(
        pool=get_agent_pool(),
    )
    return AGENT_CONTROLLER


def get_agent_service() -> "AgentService":
    global AGENT_SERVICE
    if AGENT_SERVICE is not None:
        return AGENT_SERVICE

    from roster_agent_runtime.services.agent import AgentService

    AGENT_SERVICE = AgentService(pool=get_agent_pool())
    return AGENT_SERVICE


def get_rabbitmq() -> "RabbitMQClient":
    global RABBITMQ_CLIENT
    if RABBITMQ_CLIENT is not None:
        return RABBITMQ_CLIENT

    from roster_agent_runtime.messaging.rabbitmq import RabbitMQClient

    RABBITMQ_CLIENT = RabbitMQClient()
    return RABBITMQ_CLIENT


def get_message_router() -> "MessageRouter":
    global MESSAGE_ROUTER
    if MESSAGE_ROUTER is not None:
        return MESSAGE_ROUTER

    from roster_agent_runtime.messaging.router import MessageRouter

    MESSAGE_ROUTER = MessageRouter()
    return MESSAGE_ROUTER
