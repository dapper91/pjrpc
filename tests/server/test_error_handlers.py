import json

import pjrpc
from pjrpc.server import dispatcher as pjrpc_dispatcher


def test_error_handlers(mocker):
    test_request = pjrpc.common.Request('test_method', params=dict(param='param'), id=1)
    test_context = object()
    expected_error = pjrpc.exceptions.MethodNotFoundError(data="method 'test_method' not found")
    expected_response = pjrpc.common.Response(id=1, error=expected_error)
    handler_call_order = []

    def test_any_error_handler(request, context, error):
        handler_call_order.append(test_any_error_handler)
        assert request == test_request
        assert error == expected_error
        assert context is test_context

        return error

    def test_32601_error_handler(request, context, error):
        handler_call_order.append(test_32601_error_handler)
        assert request == test_request
        assert error == expected_error
        assert context is test_context

        return error

    def test_32603_error_handler(request, context, error):
        assert False, 'should not be called'

    dispatcher = pjrpc_dispatcher.Dispatcher(
        error_handlers={
            None: [test_any_error_handler],
            -32601: [test_32601_error_handler],
            -32603: [test_32603_error_handler],
        },
    )

    request_text = json.dumps(test_request.to_json())
    response_text = dispatcher.dispatch(request_text, test_context)
    actual_response = pjrpc.common.Response.from_json(json.loads(response_text))
    assert actual_response == expected_response

    assert handler_call_order == [test_any_error_handler, test_32601_error_handler]


async def test_async_error_handlers(mocker):
    test_request = pjrpc.common.Request('test_method', params=dict(param='param'), id=1)
    test_context = object()
    expected_error = pjrpc.exceptions.MethodNotFoundError(data="method 'test_method' not found")
    expected_response = pjrpc.common.Response(id=1, error=expected_error)
    handler_call_order = []

    async def test_any_error_handler(request, context, error):
        handler_call_order.append(test_any_error_handler)
        assert request == test_request
        assert error == expected_error
        assert context is test_context

        return error

    async def test_32601_error_handler(request, context, error):
        handler_call_order.append(test_32601_error_handler)
        assert request == test_request
        assert error == expected_error
        assert context is test_context

        return error

    async def test_32603_error_handler(request, context, error):
        assert False, 'should not be called'

    dispatcher = pjrpc_dispatcher.AsyncDispatcher(
        error_handlers={
            None: [test_any_error_handler],
            -32601: [test_32601_error_handler],
            -32603: [test_32603_error_handler],
        },
    )

    request_text = json.dumps(test_request.to_json())
    response_text = await dispatcher.dispatch(request_text, test_context)
    actual_response = pjrpc.common.Response.from_json(json.loads(response_text))
    assert actual_response == expected_response

    assert handler_call_order == [test_any_error_handler, test_32601_error_handler]
