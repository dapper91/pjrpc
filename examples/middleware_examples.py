import logging
from pjrpc.common import Request
from typing import Any, Callable

RpcHandler = Callable[[Request, Any], Any]
Middleware = Callable[[Request, RpcHandler, Any], Any]


def log_requests(logger: logging.Logger) -> Middleware:
    """Return a middleware as closure which using the given logger"""

    async def mw(request: Request, context: Any, handler: RpcHandler) -> Any:
        """PJRPC Middleware which logs the execution of called RPC methods"""

        if request.is_notification:
            logger.info(f"got notification {request.method}")
            return await handler(request, context)
        logger.info(f"got call {request.method}({request.params}):")
        result = await handler(request, context)
        logger.info(f"{request.method} returned {result}")
        return result

    return mw
