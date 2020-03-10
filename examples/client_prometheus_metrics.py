import time

import prometheus_client as prom_cli
from pjrpc.client import tracer
from pjrpc.client.backend import requests as pjrpc_client

method_latency_hist = prom_cli.Histogram('method_latency', 'Method latency', labelnames=['method'])
method_call_total = prom_cli.Counter('method_call_total', 'Method call count', labelnames=['method'])
method_errors_total = prom_cli.Counter('method_errors_total', 'Method errors count', labelnames=['method', 'code'])


class PrometheusTracer(tracer.Tracer):
    def on_request_begin(self, trace_context, request):
        trace_context.started_at = time.time()
        method_call_total.labels(request.method).inc()

    def on_request_end(self, trace_context, request, response):
        method_latency_hist.labels(request.method).observe(time.time() - trace_context.started_at)
        if response.is_error:
            method_call_total.labels(request.method, response.error.code).inc()

    def on_error(self, trace_context, request, error):
        method_latency_hist.labels(request.method).observe(time.time() - trace_context.started_at)


client = pjrpc_client.Client(
    'http://localhost/api/v1', tracers=(
        PrometheusTracer(),
    ),
)

result = client.proxy.sum(1, 2)
