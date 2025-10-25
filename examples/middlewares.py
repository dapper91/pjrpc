from aiohttp import web

import pjrpc.server
from pjrpc.common import Request
from pjrpc.server.integration import aiohttp
from pjrpc.server.typedefs import AsyncHandlerType, ContextType, MiddlewareResponse

methods = pjrpc.server.MethodRegistry()


@methods.add(pass_context='request')
async def sum(request: web.Request, a: int, b: int) -> int:
    return a + b


async def middleware1(request: Request, context: ContextType, handler: AsyncHandlerType) -> MiddlewareResponse:
    print("middleware1 started")
    result = await handler(request, context)
    print("middleware1 finished")

    return result


async def middleware2(request: Request, context: ContextType, handler: AsyncHandlerType) -> MiddlewareResponse:
    print("middleware2 started")
    result = await handler(request, context)
    print("middleware2 finished")

    return result

jsonrpc_app = aiohttp.Application(
    '/api/v1',
    middlewares=[
        middleware1,
        middleware2,
    ],
)
jsonrpc_app.add_methods(methods)

if __name__ == "__main__":
    web.run_app(jsonrpc_app.http_app, host='localhost', port=8080)
