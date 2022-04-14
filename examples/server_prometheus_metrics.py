import asyncio
from typing import Any, Callable

import prometheus_client as pc
from aiohttp import web

import xjsonrpc.server
from xjsonrpc.server.integration import aiohttp

method_error_count = pc.Counter('method_error_count', 'Method error count', labelnames=['method', 'code'])
method_latency_hist = pc.Histogram('method_latency', 'Method latency', labelnames=['method'])
method_active_count = pc.Gauge('method_active_count', 'Method active count', labelnames=['method'])


async def metrics(request):
    return web.Response(body=pc.generate_latest())

http_app = web.Application()
http_app.add_routes([web.get('/metrics', metrics)])


methods = xjsonrpc.server.MethodRegistry()


@methods.add(context='context')
async def method(context: web.Request):
    print("method started")
    await asyncio.sleep(1)
    print("method finished")


async def latency_metric_middleware(request: xjsonrpc.Request, context: web.Request, handler: Callable) -> Any:
    with method_latency_hist.labels(method=request.method).time():
        return await handler(request, context)


async def active_count_metric_middleware(request: xjsonrpc.Request, context: web.Request, handler: Callable) -> Any:
    with method_active_count.labels(method=request.method).track_inprogress():
        return await handler(request, context)


async def any_error_handler(
    request: xjsonrpc.Request, context: web.Request, error: xjsonrpc.exceptions.JsonRpcError,
) -> xjsonrpc.exceptions.JsonRpcError:
    method_error_count.labels(method=request.method, code=error.code).inc()

    return error


async def validation_error_handler(
    request: xjsonrpc.Request, context: web.Request, error: xjsonrpc.exceptions.JsonRpcError,
) -> xjsonrpc.exceptions.JsonRpcError:
    print("validation error occurred")

    return error


jsonrpc_app = aiohttp.Application(
    '/api/v1',
    app=http_app,
    middlewares=(
        latency_metric_middleware,
        active_count_metric_middleware,
    ),
    error_handlers={
        -32602: [validation_error_handler],
        None: [any_error_handler],
    },
)
jsonrpc_app.dispatcher.add_methods(methods)

if __name__ == "__main__":
    web.run_app(jsonrpc_app.app, host='localhost', port=8080)
