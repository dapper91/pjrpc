from aiohttp import web

import pjrpc.server
from pjrpc.server.integration import aiohttp

methods = pjrpc.server.MethodRegistry()


@methods.add(context='request')
async def method(request):
    print("method")


async def middleware1(request, context, handler):
    print("middleware1 started")
    result = await handler(request, context)
    print("middleware1 finished")

    return result


async def middleware2(request, context, handler):
    print("middleware2 started")
    result = await handler(request, context)
    print("middleware2 finished")

    return result

jsonrpc_app = aiohttp.Application(
    '/api/v1', middlewares=(
        middleware1,
        middleware2,
    ),
)
jsonrpc_app.dispatcher.add_methods(methods)

if __name__ == "__main__":
    web.run_app(jsonrpc_app.app, host='localhost', port=8080)
