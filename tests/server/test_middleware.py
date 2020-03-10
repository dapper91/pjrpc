import json

import pjrpc
from pjrpc.server import dispatcher as pjrpc_dispatcher


def test_middleware(mocker):
    test_result = 'the result'
    test_request = pjrpc.common.Request('test_method', params=dict(param='param'), id=1)
    test_response = pjrpc.common.Response(id=1, result=test_result)
    test_context = object()
    middleware_call_order = []

    def test_method(context, param):
        assert context is test_context
        assert param == 'param'
        return test_result

    def test_middleware1(request, context, handler):
        middleware_call_order.append(test_middleware1)
        assert request == test_request
        assert context is test_context

        return handler(request, context)

    def test_middleware2(request, context, handler):
        middleware_call_order.append(test_middleware2)
        assert request == test_request
        assert context is test_context

        return handler(request, context)

    dispatcher = pjrpc_dispatcher.Dispatcher(middlewares=(test_middleware1, test_middleware2))
    dispatcher.add(test_method, 'test_method', 'context')

    request_text = json.dumps(test_request.to_json())
    response_text = dispatcher.dispatch(request_text, test_context)
    actual_response = pjrpc.common.Response.from_json(json.loads(response_text))
    assert actual_response == test_response

    assert middleware_call_order == [test_middleware1, test_middleware2]


async def test_async_middleware(mocker):
    test_result = 'the result'
    test_request = pjrpc.common.Request('test_method', params=dict(param='param'), id=1)
    test_response = pjrpc.common.Response(id=1, result=test_result)
    test_context = object()
    middleware_call_order = []

    async def test_method(context, param):
        assert context is test_context
        assert param == 'param'
        return test_result

    async def test_middleware1(request, context, handler):
        middleware_call_order.append(test_middleware1)
        assert request == test_request
        assert context is test_context

        return await handler(request, context)

    async def test_middleware2(request, context, handler):
        middleware_call_order.append(test_middleware2)
        assert request == test_request
        assert context is test_context

        return await handler(request, context)

    dispatcher = pjrpc_dispatcher.AsyncDispatcher(middlewares=(test_middleware1, test_middleware2))
    dispatcher.add(test_method, 'test_method', 'context')

    request_text = json.dumps(test_request.to_json())
    response_text = await dispatcher.dispatch(request_text, test_context)
    actual_response = pjrpc.common.Response.from_json(json.loads(response_text))
    assert actual_response == test_response

    assert middleware_call_order == [test_middleware1, test_middleware2]
