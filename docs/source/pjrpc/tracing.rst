.. _tracing:

Tracing
=======

``pjrpc`` supports client and server metrics collection. If you familiar with
`aiohttp <https://aiohttp.readthedocs.io/en/stable/web.html>`_ library it won't take a lot of time to comprehend
the metrics collection process, because ``pjrpc`` inspired by it and uses the same patterns.


client
------

The following example illustrate opentracing integration. All you need is just inherit a special class
:py:class:`pjrpc.client.Tracer` and implement required methods:

.. code-block:: python

    import opentracing
    from opentracing import tags
    from pjrpc.client import tracer
    from pjrpc.client.backend import requests as pjrpc_client


    class ClientTracer(tracer.Tracer):

        def __init__(self):
            super().__init__()
            self._tracer = opentracing.global_tracer()

        async def on_request_begin(self, trace_context, request):
            span = self._tracer.start_active_span(f'jsonrpc.{request.method}').span
            span.set_tag(tags.COMPONENT, 'pjrpc.client')
            span.set_tag(tags.SPAN_KIND, tags.SPAN_KIND_RPC_CLIENT)

        async def on_request_end(self, trace_context, request, response):
            span = self._tracer.active_span
            span.set_tag(tags.ERROR, response.is_error)
            if response.is_error:
                span.set_tag('jsonrpc.error_code', response.error.code)
                span.set_tag('jsonrpc.error_message', response.error.message)

            span.finish()

        async def on_error(self, trace_context, request, error):
            span = self._tracer.active_span
            span.set_tag(tags.ERROR, True)
            span.finish()


    client = pjrpc_client.Client(
        'http://localhost/api/v1', tracers=(
            ClientTracer(),
        ),
    )

    result = client.proxy.sum(1, 2)



server
------

On the server side you need to implement simple functions (middlewares) and pass them to the JSON-RPC application.
The following example illustrate prometheus metrics collection:

.. code-block:: python

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
