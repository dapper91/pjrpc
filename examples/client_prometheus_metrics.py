import time
from typing import Any, Mapping, Optional

import prometheus_client as prom_cli

from pjrpc import AbstractRequest, AbstractResponse, BatchRequest, Request
from pjrpc.client import MiddlewareHandler
from pjrpc.client.backend import requests as pjrpc_client

method_latency_hist = prom_cli.Histogram('method_latency', 'Method latency', labelnames=['method'])
method_call_total = prom_cli.Counter('method_call_total', 'Method call count', labelnames=['method'])
method_errors_total = prom_cli.Counter('method_errors_total', 'Method errors count', labelnames=['method', 'code'])


def prometheus_tracing_middleware(
    request: AbstractRequest,
    request_kwargs: Mapping[str, Any],
    /,
    handler: MiddlewareHandler,
) -> Optional[AbstractResponse]:
    if isinstance(request, Request):
        started_at = time.time()
        method_call_total.labels(request.method).inc()
        response = handler(request, request_kwargs)
        if response.is_error:
            method_call_total.labels(request.method, response.unwrap_error().code).inc()

        method_latency_hist.labels(request.method).observe(time.time() - started_at)

    elif isinstance(request, BatchRequest):
        response = handler(request, request_kwargs)

    else:
        raise AssertionError("unreachable")

    return response


client = pjrpc_client.Client(
    'http://localhost:8080/api/v1',
    middlewares=(
        prometheus_tracing_middleware,
    ),
)

result = client.proxy.sum(1, 2)
