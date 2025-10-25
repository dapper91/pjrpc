import json

from pjrpc.server import MethodRegistry, dispatcher, exclude_named_param, validators
from tests.common import _


def test_method_registry():
    registry = dispatcher.MethodRegistry(
        validator_factory=validators.BaseValidatorFactory(exclude=exclude_named_param('ctx')),
    )

    context = object()

    def method1():
        pass

    def method2(ctx, param1):
        assert ctx is context
        assert param1 == 'param1'

    registry.add_method(method1)
    registry.add_method(method2, name='custom_name2', pass_context='ctx')

    assert registry['method1'].func is method1
    assert registry['method1'].pass_context is False
    assert registry.get('custom_name2').func is method2
    assert registry.get('custom_name2').pass_context == 'ctx'

    registry['method1'].bind(params=())()
    registry['custom_name2'].bind(params=dict(param1='param1'), context=context)()


def test_method_registry_merge():
    registry1 = dispatcher.MethodRegistry()
    registry2 = dispatcher.MethodRegistry()

    def method1():
        pass

    registry1.add_method(method1)

    def method2():
        pass

    registry2.add_method(method2)

    registry1.merge(registry2)

    assert registry1['method1'].func is method1
    assert registry1['method2'].func is method2


def test_dispatcher():
    disp = dispatcher.Dispatcher()

    request = json.dumps({
        'jsonrpc': '2.0',
        'id': 1,
        'method': 'method',
    })

    response, error_codes = disp.dispatch(request, context=None)
    assert json.loads(response) == {
        'jsonrpc': '2.0',
        'id': 1,
        'error': {
            'code': -32601,
            'message': 'Method not found',
            'data': "method 'method' not found",
        },
    }

    request = json.dumps({
        'jsonrpc': '2.0',
        'id': None,
        'method': 'method',
    })

    assert disp.dispatch(request, context=None) is None

    def method1(param):
        return param

    registry = MethodRegistry()
    registry.add_method(method1)
    disp.add_methods(registry)

    request = json.dumps({
        'jsonrpc': '2.0',
        'id': 1,
        'method': 'method1',
        'params': ['param1'],
    })

    response, error_codes = disp.dispatch(request, context=None)
    assert json.loads(response) == {
        'jsonrpc': '2.0',
        'id': 1,
        'result': 'param1',
    }

    def method2():
        raise Exception('unhandled error')

    registry = MethodRegistry()
    registry.add_method(method2)
    disp.add_methods(registry)

    request = json.dumps({
        'jsonrpc': '2.0',
        'id': 1,
        'method': 'method2',
    })

    response, error_codes = disp.dispatch(request, context=None)
    assert json.loads(response) == {
        'jsonrpc': '2.0',
        'id': 1,
        'error': {
            'code': -32000,
            'message': 'Server error',
        },
    }

    request = json.dumps([
        {
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'method1',
            'params': ['param1'],
        },
        {
            'jsonrpc': '2.0',
            'id': None,
            'method': 'method1',
            'params': ['param2'],
        },
        {
            'jsonrpc': '2.0',
            'id': 2,
            'method': 'method3',
        },
    ])

    response, error_codes = disp.dispatch(request, context=None)
    assert json.loads(response) == [
        {
            'jsonrpc': '2.0',
            'id': 1,
            'result': 'param1',
        },
        {
            'jsonrpc': '2.0',
            'id': 2,
            'error': {
                'code': -32601,
                'message': 'Method not found',
                'data': "method 'method3' not found",
            },
        },
    ]


def test_dispatcher_errors():
    disp = dispatcher.Dispatcher()

    response, error_codes = disp.dispatch('', context=None)
    assert json.loads(response) == {
        'jsonrpc': '2.0',
        'id': None,
        'error': {
            'code': -32700,
            'message': 'Parse error',
            'data': _,
        },
    }

    response, error_codes = disp.dispatch('{}', context=None)
    assert json.loads(response) == {
        'jsonrpc': '2.0',
        'id': None,
        'error': {
            'code': -32600,
            'message': 'Invalid Request',
            'data': _,
        },
    }

    response, error_codes = disp.dispatch('[]', context=None)
    assert json.loads(response) == {
        'jsonrpc': '2.0',
        'id': None,
        'error': {
            'code': -32600,
            'message': 'Invalid Request',
            'data': _,
        },
    }


def test_dispatcher_batch_too_large_errors():
    disp = dispatcher.Dispatcher(max_batch_size=1)

    request = json.dumps(
        [
            {
                'jsonrpc': '2.0',
                'id': 1,
                'method': 'method',
            },
            {
                'jsonrpc': '2.0',
                'id': 2,
                'method': 'method',
            },
        ],
    )

    response, error_codes = disp.dispatch(request, context=None)
    assert json.loads(response) == {
        'jsonrpc': '2.0',
        'id': None,
        'error': {
            'code': -32600,
            'message': 'Invalid Request',
            'data': "batch too large",
        },
    }


async def test_async_dispatcher():
    disp = dispatcher.AsyncDispatcher()

    request = json.dumps({
        'jsonrpc': '2.0',
        'id': 1,
        'method': 'method',
    })

    response, error_codes = await disp.dispatch(request, context=None)
    assert json.loads(response) == {
        'jsonrpc': '2.0',
        'id': 1,
        'error': {
            'code': -32601,
            'message': 'Method not found',
            'data': "method 'method' not found",
        },
    }

    request = json.dumps({
        'jsonrpc': '2.0',
        'id': None,
        'method': 'method',
    })

    assert await disp.dispatch(request, context=None) is None

    async def method1(param):
        return param

    registry = MethodRegistry()
    registry.add_method(method1)
    disp.add_methods(registry)

    request = json.dumps({
        'jsonrpc': '2.0',
        'id': 1,
        'method': 'method1',
        'params': ['param1'],
    })

    response, error_codes = await disp.dispatch(request, context=None)
    assert json.loads(response) == {
        'jsonrpc': '2.0',
        'id': 1,
        'result': 'param1',
    }

    async def method2():
        raise Exception('unhandled error')

    registry = MethodRegistry()
    registry.add_method(method2)
    disp.add_methods(registry)

    request = json.dumps({
        'jsonrpc': '2.0',
        'id': 1,
        'method': 'method2',
    })

    response, error_codes = await disp.dispatch(request, context=None)
    assert json.loads(response) == {
        'jsonrpc': '2.0',
        'id': 1,
        'error': {
            'code': -32000,
            'message': 'Server error',
        },
    }

    request = json.dumps([
        {
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'method1',
            'params': ['param1'],
        },
        {
            'jsonrpc': '2.0',
            'id': None,
            'method': 'method1',
            'params': ['param2'],
        },
        {
            'jsonrpc': '2.0',
            'id': 2,
            'method': 'method3',
        },
    ])

    response, error_codes = await disp.dispatch(request, context=None)
    assert json.loads(response) == [
        {
            'jsonrpc': '2.0',
            'id': 1,
            'result': 'param1',
        },
        {
            'jsonrpc': '2.0',
            'id': 2,
            'error': {
                'code': -32601,
                'message': 'Method not found',
                'data': "method 'method3' not found",
            },
        },
    ]


async def test_async_dispatcher_errors():
    disp = dispatcher.AsyncDispatcher()

    response, error_codes = await disp.dispatch('', context=None)
    assert json.loads(response) == {
        'jsonrpc': '2.0',
        'id': None,
        'error': {
            'code': -32700,
            'message': 'Parse error',
            'data': _,
        },
    }

    response, error_codes = await disp.dispatch('{}', context=None)
    assert json.loads(response) == {
        'jsonrpc': '2.0',
        'id': None,
        'error': {
            'code': -32600,
            'message': 'Invalid Request',
            'data': _,
        },
    }


async def test_async_dispatcher_batch_too_large_errors():
    disp = dispatcher.AsyncDispatcher(max_batch_size=1)

    request = json.dumps(
        [
            {
                'jsonrpc': '2.0',
                'id': 1,
                'method': 'method',
            },
            {
                'jsonrpc': '2.0',
                'id': 2,
                'method': 'method',
            },
        ],
    )

    response, error_codes = await disp.dispatch(request, context=None)
    assert json.loads(response) == {
        'jsonrpc': '2.0',
        'id': None,
        'error': {
            'code': -32600,
            'message': 'Invalid Request',
            'data': "batch too large",
        },
    }
