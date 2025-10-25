import asyncio

import prometheus_client as pc
from aiohttp import web

import pjrpc.server
from pjrpc import Request, Response
from pjrpc.server import AsyncHandlerType
from pjrpc.server.integration import aiohttp

method_error_count = pc.Counter('method_error_count', 'Method error count', labelnames=['method', 'code'])
method_latency_hist = pc.Histogram('method_latency', 'Method latency', labelnames=['method'])
method_active_count = pc.Gauge('method_active_count', 'Method active count', labelnames=['method'])


async def metrics(request):
    return web.Response(body=pc.generate_latest())

http_app = web.Application()
http_app.add_routes([web.get('/metrics', metrics)])


methods = pjrpc.server.MethodRegistry()


@methods.add(pass_context='context')
async def sum(context: web.Request, a: int, b: int) -> int:
    print("method started")
    await asyncio.sleep(1)
    print("method finished")

    return a + b


async def latency_metric_middleware(request: Request, context: web.Request, handler: AsyncHandlerType) -> Response:
    with method_latency_hist.labels(method=request.method).time():
        return await handler(request, context)


async def active_count_metric_middleware(request: Request, context: web.Request, handler: AsyncHandlerType) -> Response:
    with method_active_count.labels(method=request.method).track_inprogress():
        return await handler(request, context)


async def error_counter_middleware(request: Request, context: web.Request, handler: AsyncHandlerType) -> Response:
    if response := await handler(request, context):
        if response.is_error:
            method_error_count.labels(method=request.method, code=response.unwrap_error().code).inc()

    return response


jsonrpc_app = aiohttp.Application(
    '/api/v1',
    http_app=http_app,
    middlewares=(
        latency_metric_middleware,
        active_count_metric_middleware,
        error_counter_middleware,
    ),
)
jsonrpc_app.add_methods(methods)

if __name__ == "__main__":
    web.run_app(jsonrpc_app.http_app, host='localhost', port=8080)
