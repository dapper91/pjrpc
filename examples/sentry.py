import sentry_sdk
from aiohttp import web

import pjrpc.server
from pjrpc.common import Request, Response
from pjrpc.server import AsyncHandlerType
from pjrpc.server.integration import aiohttp

methods = pjrpc.server.MethodRegistry()


@methods.add(pass_context='request')
async def sum(request: web.Request, a: int, b: int) -> int:
    return a + b


async def sentry_middleware(request: Request, context: web.Request, handler: AsyncHandlerType) -> Response:
    try:
        return await handler(request, context)
    except pjrpc.exceptions.JsonRpcError as e:
        sentry_sdk.capture_exception(e)
        raise


jsonrpc_app = aiohttp.Application(
    '/api/v1', middlewares=(
        sentry_middleware,
    ),
)
jsonrpc_app.add_methods(methods)

if __name__ == "__main__":
    web.run_app(jsonrpc_app.http_app, host='localhost', port=8080)
