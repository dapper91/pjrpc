import asyncio

import prometheus_client
from aiohttp import web

import pjrpc.server
from pjrpc.server.integration import aiohttp

method_latency_hist = prometheus_client.Histogram('method_latency', 'Method latency', labelnames=['method'])
method_active_count = prometheus_client.Gauge('method_active_count', 'Method active count', labelnames=['method'])


async def metrics(request):
    return web.Response(body=prometheus_client.generate_latest())

http_app = web.Application()
http_app.add_routes([web.get('/metrics', metrics)])


methods = pjrpc.server.MethodRegistry()


@methods.add(context='context')
async def method(context):
    print("method started")
    await asyncio.sleep(1)
    print("method finished")


async def latency_metric_middleware(request, context, handler):
    with method_latency_hist.labels(method=request.method).time():
        return await handler(request, context)


async def active_count_metric_middleware(request, context, handler):
    with method_active_count.labels(method=request.method).track_inprogress():
        return await handler(request, context)

jsonrpc_app = aiohttp.Application(
    '/api/v1', app=http_app, middlewares=(
        latency_metric_middleware,
        active_count_metric_middleware,
    ),
)
jsonrpc_app.dispatcher.add_methods(methods)

if __name__ == "__main__":
    web.run_app(jsonrpc_app.app, host='localhost', port=8080)
