import json
from pjrpc.common import BatchRequest, BatchResponse, Request, Response
from pjrpc import client

import pytest


@pytest.mark.parametrize(
    'req, resp, exc', [
        (
            Request(id=1, method='method', params=[1, '2']),
            Response(id=1, result='result'),
            None,
        ),
        (
            BatchRequest(Request(id=1, method='method', params=[1, '2'])),
            BatchResponse(Response(id=1, result='result')),
            None,
        ),
        (
            BatchRequest(Request(id=1, method='method', params=[1, '2'])),
            None,
            BaseException(),
        ),
    ],
)
def test_request_tracing(mocker, req, resp, exc):

    class Client(client.AbstractClient):
        def _request(self, request_text, is_notification=False, **kwargs):
            if exc:
                raise exc
            return json.dumps(resp.to_json())

    class Tracer(client.Tracer):
        on_request_begin = mocker.Mock('on_request_begin')
        on_request_end = mocker.Mock('on_request_end')
        on_error = mocker.Mock('on_error')

    tracer = Tracer()
    cli = Client(tracers=(tracer,))

    trace_ctx = object()

    if exc:
        with pytest.raises(BaseException):
            cli.send(req, _trace_ctx=trace_ctx)
        tracer.on_error.assert_called_once_with(trace_ctx, req, exc)

    else:
        if isinstance(req, BatchRequest):
            cli.batch.send(req, _trace_ctx=trace_ctx)
        else:
            cli.send(req, _trace_ctx=trace_ctx)

        tracer.on_request_begin.assert_called_once_with(trace_ctx, req)
        tracer.on_request_end.assert_called_once_with(trace_ctx, req, resp)


@pytest.mark.parametrize(
    'req, resp, exc', [
        (
            Request(id=1, method='method', params=[1, '2']),
            Response(id=1, result='result'),
            None,
        ),
        (
            BatchRequest(Request(id=1, method='method', params=[1, '2'])),
            BatchResponse(Response(id=1, result='result')),
            None,
        ),
        (
            BatchRequest(Request(id=1, method='method', params=[1, '2'])),
            None,
            BaseException(),
        ),
    ],
)
async def test_async_request_tracing(mocker, req, resp, exc):

    class Client(client.AbstractAsyncClient):
        async def _request(self, request_text, is_notification=False, **kwargs):
            if exc:
                raise exc
            return json.dumps(resp.to_json())

    class Tracer(client.Tracer):
        on_request_begin = mocker.Mock('on_request_begin')
        on_request_end = mocker.Mock('on_request_end')
        on_error = mocker.Mock('on_error')

    tracer = Tracer()
    cli = Client(tracers=(tracer,))

    trace_ctx = object()

    if exc:
        with pytest.raises(BaseException):
            await cli.send(req, _trace_ctx=trace_ctx)
        tracer.on_error.assert_called_once_with(trace_ctx, req, exc)

    else:
        if isinstance(req, BatchRequest):
            await cli.batch.send(req, _trace_ctx=trace_ctx)
        else:
            await cli.send(req, _trace_ctx=trace_ctx)

        tracer.on_request_begin.assert_called_once_with(trace_ctx, req)
        tracer.on_request_end.assert_called_once_with(trace_ctx, req, resp)
