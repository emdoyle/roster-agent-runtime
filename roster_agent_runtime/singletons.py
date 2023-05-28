from typing import Optional

from roster_agent_runtime.controllers.agent import AgentController
from roster_agent_runtime.executors import AgentExecutor
from roster_agent_runtime.informers.roster import RosterInformer
from roster_agent_runtime.notifier import RosterNotifier
from roster_agent_runtime.services.agent import AgentService

ROSTER_INFORMER: Optional[RosterInformer] = None
ROSTER_NOTIFIER: Optional[RosterNotifier] = None
AGENT_EXECUTOR: Optional[AgentExecutor] = None
AGENT_CONTROLLER: Optional[AgentController] = None
AGENT_SERVICE: Optional[AgentService] = None


def get_roster_informer() -> RosterInformer:
    global ROSTER_INFORMER
    if ROSTER_INFORMER is not None:
        return ROSTER_INFORMER

    ROSTER_INFORMER = RosterInformer()
    return ROSTER_INFORMER


def get_roster_notifier() -> RosterNotifier:
    global ROSTER_NOTIFIER
    if ROSTER_NOTIFIER is not None:
        return ROSTER_NOTIFIER

    ROSTER_NOTIFIER = RosterNotifier()
    return ROSTER_NOTIFIER


def get_agent_executor() -> AgentExecutor:
    global AGENT_EXECUTOR
    if AGENT_EXECUTOR is not None:
        return AGENT_EXECUTOR

    # TODO: Make this configurable
    from roster_agent_runtime.executors.docker import DockerAgentExecutor

    AGENT_EXECUTOR = DockerAgentExecutor()

    return AGENT_EXECUTOR


def get_agent_controller() -> AgentController:
    global AGENT_CONTROLLER
    if AGENT_CONTROLLER is not None:
        return AGENT_CONTROLLER

    AGENT_CONTROLLER = AgentController(
        executor=get_agent_executor(),
        roster_informer=get_roster_informer(),
        roster_notifier=get_roster_notifier(),
    )
    return AGENT_CONTROLLER


def get_agent_service() -> AgentService:
    global AGENT_SERVICE
    if AGENT_SERVICE is not None:
        return AGENT_SERVICE

    AGENT_SERVICE = AgentService(executor=get_agent_executor())
    return AGENT_SERVICE
