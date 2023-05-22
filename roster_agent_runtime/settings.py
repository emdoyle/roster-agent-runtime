from environs import Env

env = Env()
env.read_env()

DEBUG = env.bool("ROSTER_RUNTIME_DEBUG", False)

PORT = env.int("ROSTER_RUNTIME_PORT", 7890)

ROSTER_API_URL = env.str("ROSTER_API_URL", "http://localhost:8080")
ROSTER_API_EVENTS_PATH = env.str("ROSTER_API_EVENTS_PATH", "/events")
ROSTER_API_EVENTS_URL = ROSTER_API_URL + ROSTER_API_EVENTS_PATH
