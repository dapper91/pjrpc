import asyncio

import opentracing
from opentracing import tags
from aiohttp import web

import pjrpc.server
from pjrpc.server.integration import aiohttp


@web.middleware
async def http_tracing_middleware(request, handler):
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
        response: web.Response = await handler(request)
        span.set_tag(tags.HTTP_STATUS_CODE, response.status)
        span.set_tag(tags.ERROR, response.status >= 400)

    return response

http_app = web.Application(
    middlewares=(
        http_tracing_middleware,
    ),
)

methods = pjrpc.server.MethodRegistry()


@methods.add(context='context')
async def method(context):
    print("method started")
    await asyncio.sleep(1)
    print("method finished")


async def jsonrpc_tracing_middleware(request, context, handler):
    tracer = opentracing.global_tracer()
    span = tracer.start_span(f'jsonrpc.{request.method}')

    span.set_tag(tags.COMPONENT, 'pjrpc')
    span.set_tag(tags.SPAN_KIND, tags.SPAN_KIND_RPC_SERVER)
    span.set_tag('jsonrpc.version', request.version)
    span.set_tag('jsonrpc.id', request.id)
    span.set_tag('jsonrpc.method', request.method)

    with tracer.scope_manager.activate(span, finish_on_close=True):
        response = await handler(request, context)
        if response.is_error:
            span.set_tag('jsonrpc.error_code', response.error.code)
            span.set_tag('jsonrpc.error_message', response.error.message)
            span.set_tag(tags.ERROR, True)
        else:
            span.set_tag(tags.ERROR, False)

    return response

jsonrpc_app = aiohttp.Application(
    '/api/v1', app=http_app, middlewares=(
        jsonrpc_tracing_middleware,
    ),
)
jsonrpc_app.dispatcher.add_methods(methods)

if __name__ == "__main__":
    web.run_app(jsonrpc_app.app, host='localhost', port=8080)
