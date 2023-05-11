from typing import Callable, Type

from fastapi.routing import APIRoute


def create_error_handling_route():
    class ErrorHandlingRoute(APIRoute):
        exception_handlers = {}

        @classmethod
        def exception_handler(cls, exception_cls: Type[Exception]):
            def decorator(exception_handler: Callable):
                cls.exception_handlers[exception_cls] = exception_handler
                return exception_handler

            return decorator

        def get_route_handler(self) -> Callable:
            original_route_handler = super().get_route_handler()

            async def custom_route_handler(request):
                try:
                    return await original_route_handler(request)
                except Exception as exc:
                    for exception_cls in type(exc).__mro__:
                        if exception_cls in self.exception_handlers:
                            handler = self.exception_handlers[exception_cls]
                            return await handler(request, exc)
                    raise

            return custom_route_handler

    return ErrorHandlingRoute
