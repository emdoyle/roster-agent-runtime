import asyncio

from roster_agent_runtime.controllers.agent import get_agent_controller


def run():
    controller = get_agent_controller()

    loop = asyncio.get_event_loop()

    try:
        loop.run_until_complete(controller.setup())
        loop.run_until_complete(controller.run())
    except KeyboardInterrupt:
        pass
    finally:
        loop.run_until_complete(controller.teardown())
        loop.stop()
        loop.close()


if __name__ == "__main__":
    run()
