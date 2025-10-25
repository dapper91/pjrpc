.. _tracing:

Tracing
=======

``pjrpc`` supports client and server metrics collection.


client
------

The following example illustrate opentracing integration.

.. code-block:: python

    from typing import Any, Mapping, Optional

    import opentracing
    from opentracing import propagation, tags

    from pjrpc.client import MiddlewareHandler
    from pjrpc.client.backend import requests as pjrpc_client
    from pjrpc.common import AbstractRequest, AbstractResponse, BatchRequest, Request

    tracer = opentracing.global_tracer()


    def tracing_middleware(
        request: AbstractRequest,
        request_kwargs: Mapping[str, Any],
        /,
        handler: MiddlewareHandler,
    ) -> Optional[AbstractResponse]:
        if isinstance(request, Request):
            span = tracer.start_active_span(f'jsonrpc.{request.method}').span
            span.set_tag(tags.COMPONENT, 'pjrpc.client')
            span.set_tag(tags.SPAN_KIND, tags.SPAN_KIND_RPC_CLIENT)
            if http_headers := request_kwargs.get('headers', {}):
                tracer.inject(
                    span_context=span,
                    format=propagation.Format.HTTP_HEADERS,
                    carrier=http_headers,
                )

            response = handler(request, request_kwargs)
            if response.is_error:
                span = tracer.active_span
                span.set_tag(tags.ERROR, response.is_error)
                span.set_tag('jsonrpc.error_code', response.unwrap_error().code)
                span.set_tag('jsonrpc.error_message', response.unwrap_error().message)

                span.finish()

        elif isinstance(request, BatchRequest):
            response = handler(request, request_kwargs)

        else:
            raise AssertionError("unreachable")

        return response


    client = pjrpc_client.Client(
        'http://localhost:8080/api/v1',
        middlewares=[
            tracing_middleware,
        ],
    )

    result = client.proxy.sum(1, 2)



server
------

On the server side you need to implement simple functions (middlewares) and pass them to the JSON-RPC application.
The following example illustrate prometheus metrics collection:

.. code-block:: python

    import asyncio

    import opentracing
    from aiohttp import web
    from aiohttp.typedefs import Handler as HttpHandler
    from opentracing import tags

    import pjrpc.server
    from pjrpc import Request, Response
    from pjrpc.server import AsyncHandlerType
    from pjrpc.server.integration import aiohttp

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
        middlewares=[
            jsonrpc_tracing_middleware,
        ],
    )
    jsonrpc_app.add_methods(methods)

    if __name__ == "__main__":
        web.run_app(jsonrpc_app.http_app, host='localhost', port=8080)
