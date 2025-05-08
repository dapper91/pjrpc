import opentracing
from opentracing import propagation, tags

from pjrpc.client import tracer
from pjrpc.client.backend import requests as pjrpc_client


class ClientTracer(tracer.Tracer):

    def __init__(self):
        super().__init__()
        self._tracer = opentracing.global_tracer()

    def on_request_begin(self, trace_context, request, request_kwargs):
        span = self._tracer.start_active_span(f'jsonrpc.{request.method}').span
        span.set_tag(tags.COMPONENT, 'pjrpc.client')
        span.set_tag(tags.SPAN_KIND, tags.SPAN_KIND_RPC_CLIENT)

        http_headers = request_kwargs.setdefault('headers', {})
        self._tracer.inject(
            span_context=span,
            format=propagation.Format.HTTP_HEADERS,
            carrier=http_headers,
        )

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


client = pjrpc_client.Client(
    'http://localhost/api/v1', tracers=(
        ClientTracer(),
    ),
)

result = client.proxy.sum(1, 2)
