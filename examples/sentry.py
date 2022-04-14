import sentry_sdk
from aiohttp import web

import xjsonrpc.server
from xjsonrpc.server.integration import aiohttp

methods = xjsonrpc.server.MethodRegistry()


@methods.add(context='request')
async def method(request):
    print("method")


async def sentry_middleware(request, context, handler):
    try:
        return await handler(request, context)
    except xjsonrpc.exceptions.JsonRpcError as e:
        sentry_sdk.capture_exception(e)
        raise


jsonrpc_app = aiohttp.Application(
    '/api/v1', middlewares=(
        sentry_middleware,
    ),
)
jsonrpc_app.dispatcher.add_methods(methods)

if __name__ == "__main__":
    web.run_app(jsonrpc_app.app, host='localhost', port=8080)
