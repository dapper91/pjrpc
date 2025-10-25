import asyncio

import opentracing
from aiohttp import web
from aiohttp.typedefs import Handler as HttpHandler
from opentracing import tags

import pjrpc.server
from pjrpc import Request, Response
from pjrpc.server import AsyncHandlerType
from pjrpc.server.integration import aiohttp


@web.middleware
async def http_tracing_middleware(request: web.Request, handler: HttpHandler) -> web.StreamResponse:
    """
    aiohttp server tracer.
    """

    tracer = opentracing.global_tracer()
    try:
        span_ctx = tracer.extract(format=opentracing.Format.HTTP_HEADERS, carrier=request.headers)
    except (opentracing.InvalidCarrierException, opentracing.SpanContextCorruptedException):
        span_ctx = None

    span = tracer.start_span(f'http.{request.method}', child_of=span_ctx)
    span.set_tag(tags.COMPONENT, 'aiohttp.server')
    span.set_tag(tags.SPAN_KIND, tags.SPAN_KIND_RPC_SERVER)
    span.set_tag(tags.PEER_ADDRESS, request.remote)
    span.set_tag(tags.HTTP_URL, str(request.url))
    span.set_tag(tags.HTTP_METHOD, request.method)

    with tracer.scope_manager.activate(span, finish_on_close=True):
        response = await handler(request)
        span.set_tag(tags.HTTP_STATUS_CODE, response.status)
        span.set_tag(tags.ERROR, response.status >= 400)

    return response

http_app = web.Application(
    middlewares=(
        http_tracing_middleware,
    ),
)

methods = pjrpc.server.MethodRegistry()


@methods.add(pass_context='context')
async def sum(context: web.Request, a: int, b: int) -> int:
    print("method started")
    await asyncio.sleep(1)
    print("method finished")

    return a + b


async def jsonrpc_tracing_middleware(request: Request, context: web.Request, handler: AsyncHandlerType) -> Response:
    tracer = opentracing.global_tracer()
    span = tracer.start_span(f'jsonrpc.{request.method}')

    span.set_tag(tags.COMPONENT, 'pjrpc')
    span.set_tag(tags.SPAN_KIND, tags.SPAN_KIND_RPC_SERVER)
    span.set_tag('jsonrpc.version', request.version)
    span.set_tag('jsonrpc.id', request.id)
    span.set_tag('jsonrpc.method', request.method)

    with tracer.scope_manager.activate(span, finish_on_close=True):
        if response := await handler(request, context):
            if response.is_error:
                span.set_tag('jsonrpc.error_code', response.error.code)
                span.set_tag('jsonrpc.error_message', response.error.message)
                span.set_tag(tags.ERROR, True)
            else:
                span.set_tag(tags.ERROR, False)

    return response

jsonrpc_app = aiohttp.Application(
    '/api/v1',
    http_app=http_app,
    middlewares=[
        jsonrpc_tracing_middleware,
    ],
)
jsonrpc_app.add_methods(methods)

if __name__ == "__main__":
    web.run_app(jsonrpc_app.http_app, host='localhost', port=8080)
