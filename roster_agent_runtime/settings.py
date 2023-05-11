from environs import Env

env = Env()
env.read_env()

DEBUG = env.bool("ROSTER_RUNTIME_DEBUG", False)

PORT = env.int("ROSTER_RUNTIME_PORT", 7890)
