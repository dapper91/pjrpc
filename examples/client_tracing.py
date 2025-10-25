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
