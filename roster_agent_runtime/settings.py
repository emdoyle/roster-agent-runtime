import logging

from environs import Env

env = Env()
env.read_env()

DEBUG = env.bool("ROSTER_RUNTIME_DEBUG", False)
LOG = env.str("ROSTER_RUNTIME_LOG", "app.log")
LOG_LEVEL = getattr(logging, env.str("ROSTER_RUNTIME_LOG_LEVEL", "DEBUG"), "DEBUG")

PORT = env.int("ROSTER_RUNTIME_PORT", 7890)

ROSTER_API_URL = env.str("ROSTER_RUNTIME_API_URL", "http://localhost:7888")
ROSTER_API_EVENTS_PATH = env.str("ROSTER_RUNTIME_API_EVENTS_PATH", "/agent-events")
ROSTER_API_EVENTS_URL = ROSTER_API_URL + ROSTER_API_EVENTS_PATH
ROSTER_API_STATUS_UPDATE_PATH = env.str(
    "ROSTER_RUNTIME_API_STATUS_UPDATE_PATH", "/status-update"
)
ROSTER_API_STATUS_UPDATE_URL = ROSTER_API_URL + ROSTER_API_STATUS_UPDATE_PATH
