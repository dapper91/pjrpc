import opentracing
from opentracing import tags
from xjsonrpc.client import tracer
from xjsonrpc.client.backend import requests as xjsonrpc_client


class ClientTracer(tracer.Tracer):

    def __init__(self):
        super().__init__()
        self._tracer = opentracing.global_tracer()

    def on_request_begin(self, trace_context, request):
        span = self._tracer.start_active_span(f'jsonrpc.{request.method}').span
        span.set_tag(tags.COMPONENT, 'xjsonrpc.client')
        span.set_tag(tags.SPAN_KIND, tags.SPAN_KIND_RPC_CLIENT)

    def on_request_end(self, trace_context, request, response):
        span = self._tracer.active_span
        span.set_tag(tags.ERROR, response.is_error)
        if response.is_error:
            span.set_tag('jsonrpc.error_code', response.error.code)
            span.set_tag('jsonrpc.error_message', response.error.message)

        span.finish()

    def on_error(self, trace_context, request, error):
        span = self._tracer.active_span
        span.set_tag(tags.ERROR, True)
        span.finish()


client = xjsonrpc_client.Client(
    'http://localhost/api/v1', tracers=(
        ClientTracer(),
    ),
)

result = client.proxy.sum(1, 2)
