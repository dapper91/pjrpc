import json

import pjrpc
from pjrpc.server.dispatcher import AsyncDispatcher, Dispatcher, MethodRegistry
from pjrpc.server.utils import exclude_positional_param
from pjrpc.server.validators import BaseValidatorFactory


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

    registry = MethodRegistry(validator_factory=BaseValidatorFactory(exclude=exclude_positional_param(0)))
    registry.add_method(test_method, 'test_method', pass_context=True)

    dispatcher = Dispatcher(middlewares=(test_middleware1, test_middleware2))
    dispatcher.add_methods(registry)

    request_text = json.dumps(test_request.to_json())
    response_text, error_codes = dispatcher.dispatch(request_text, test_context)
    actual_response = pjrpc.common.Response.from_json(json.loads(response_text))
    assert actual_response == test_response
    assert error_codes == (0,)

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

    registry = MethodRegistry(validator_factory=BaseValidatorFactory(exclude=exclude_positional_param(0)))
    registry.add_method(test_method, 'test_method', pass_context=True)

    dispatcher = AsyncDispatcher(middlewares=(test_middleware1, test_middleware2))
    dispatcher.add_methods(registry)

    request_text = json.dumps(test_request.to_json())
    response_text, error_codes = await dispatcher.dispatch(request_text, test_context)
    actual_response = pjrpc.common.Response.from_json(json.loads(response_text))
    assert actual_response == test_response
    assert error_codes == (0,)

    assert middleware_call_order == [test_middleware1, test_middleware2]
