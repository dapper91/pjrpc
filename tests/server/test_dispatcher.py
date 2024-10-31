import json

from pjrpc.server import Method, ViewMixin, dispatcher, validators
from tests.common import _


def test_method_registry():
    registry = dispatcher.MethodRegistry()

    context = object()

    def method1():
        pass

    def method2(ctx, param1):
        assert ctx is context
        assert param1 == 'param1'

    registry.add_methods(
        method1,
        Method(method2, name='custom_name2', context='ctx'),
    )

    assert registry['method1'].method is method1
    assert registry['method1'].context is None
    assert registry.get('custom_name2').method is method2
    assert registry.get('custom_name2').context == 'ctx'

    registry['method1'].bind(params=())()
    registry['custom_name2'].bind(params=dict(param1='param1'), context=context)()


async def test_method_registry_prefix():
    registry = dispatcher.MethodRegistry(prefix='prefix')

    context = object()

    async def method1():
        pass

    async def method2(ctx, param1):
        assert ctx is context
        assert param1 == 'param1'

    registry.add(method1)
    registry.add(method2, 'custom_name2', context='ctx')

    assert registry['prefix.method1'].method is method1
    assert registry['prefix.method1'].context is None
    assert registry.get('prefix.custom_name2').method is method2
    assert registry.get('prefix.custom_name2').context == 'ctx'

    await registry['prefix.method1'].bind(params=())()
    await registry['prefix.custom_name2'].bind(params=('param1',), context=context)()


def test_method_registry_merge():
    registry1 = dispatcher.MethodRegistry()
    registry2 = dispatcher.MethodRegistry()

    def method1():
        pass

    registry1.add(method1)

    def method2():
        pass

    registry2.add(method2)

    registry1.merge(registry2)

    assert registry1['method1'].method is method1
    assert registry1['method2'].method is method2


def test_method_registry_merge_prefix():
    registry1 = dispatcher.MethodRegistry(prefix='prefix1')
    registry2 = dispatcher.MethodRegistry(prefix='prefix2')

    def test_method():
        pass

    registry1.add(test_method, name='method1', context='ctx1')
    registry2.add(test_method, name='method2', context='ctx2')

    assert list(registry1.items()) == [('prefix1.method1', Method(test_method, 'prefix1.method1', 'ctx1'))]
    assert list(registry2.items()) == [('prefix2.method2', Method(test_method, 'prefix2.method2', 'ctx2'))]

    registry2.merge(registry1)

    assert list(registry2.items()) == [
        ('prefix2.method2', Method(test_method, 'prefix2.method2', 'ctx2')),
        ('prefix2.prefix1.method1', Method(test_method, 'prefix2.prefix1.method1', 'ctx1')),
    ]


async def test_method_registry_view():
    registry = dispatcher.MethodRegistry()
    validator = validators.BaseValidator()
    validator_args = {'arg': 'value'}

    class MethodView(ViewMixin):
        @validator.validate(**validator_args)
        def method1(self):
            pass

        @validator.validate(**validator_args)
        async def method2(self, param1):
            assert param1 == 'param1'

    registry.view(MethodView, prefix='view')

    assert registry['view.method1'].validator == validator
    assert registry['view.method1'].validator_args == validator_args
    assert registry['view.method2'].validator == validator
    assert registry['view.method2'].validator_args == validator_args


async def test_method_view_validation():
    registry = dispatcher.MethodRegistry()

    context = object()

    class MethodView(ViewMixin):

        def __init__(self, ctx):
            assert ctx is context

        def method1(self):
            pass

        async def method2(self, param1):
            assert param1 == 'param1'

    registry.view(MethodView, prefix='view', context='ctx')

    assert registry['view.method1'].view_cls is MethodView
    assert registry.get('view.method2').view_cls is MethodView

    registry['view.method1'].bind(params=(), context=context)()
    await registry['view.method2'].bind(params=('param1',), context=context)()


def test_dispatcher():
    disp = dispatcher.Dispatcher()

    request = json.dumps({
        'jsonrpc': '2.0',
        'id': 1,
        'method': 'method',
    })

    response, error_codes = disp.dispatch(request)
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

    assert disp.dispatch(request) is None

    def method1(param):
        return param

    disp.add(method1)

    request = json.dumps({
        'jsonrpc': '2.0',
        'id': 1,
        'method': 'method1',
        'params': ['param1'],
    })

    response, error_codes = disp.dispatch(request)
    assert json.loads(response) == {
        'jsonrpc': '2.0',
        'id': 1,
        'result': 'param1',
    }

    def method2():
        raise Exception('unhandled error')

    disp.add(method2)

    request = json.dumps({
        'jsonrpc': '2.0',
        'id': 1,
        'method': 'method2',
    })

    response, error_codes = disp.dispatch(request)
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

    response, error_codes = disp.dispatch(request)
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

    response, error_codes = disp.dispatch('')
    assert json.loads(response) == {
        'jsonrpc': '2.0',
        'id': None,
        'error': {
            'code': -32700,
            'message': 'Parse error',
            'data': _,
        },
    }

    response, error_codes = disp.dispatch('{}')
    assert json.loads(response) == {
        'jsonrpc': '2.0',
        'id': None,
        'error': {
            'code': -32600,
            'message': 'Invalid Request',
            'data': _,
        },
    }

    response, error_codes = disp.dispatch('[]')
    assert json.loads(response) == {
        'jsonrpc': '2.0',
        'id': None,
        'error': {
            'code': -32600,
            'message': 'Invalid Request',
            'data': _,
        },
    }

    request = json.dumps([
        {
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'method',
        },
        {
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'method',
        },
    ])

    response, error_codes = disp.dispatch(request)
    assert json.loads(response) == {
        'jsonrpc': '2.0',
        'id': None,
        'error': {
            'code': -32600,
            'message': 'Invalid Request',
            'data': 'request id duplicates found: 1',
        },
    }

    response, error_codes = disp.dispatch(request)
    assert json.loads(response) == {
        'jsonrpc': '2.0',
        'id': None,
        'error': {
            'code': -32600,
            'message': 'Invalid Request',
            'data': 'request id duplicates found: 1',
        },
    }


async def test_async_dispatcher():
    disp = dispatcher.AsyncDispatcher()

    request = json.dumps({
        'jsonrpc': '2.0',
        'id': 1,
        'method': 'method',
    })

    response, error_codes = await disp.dispatch(request)
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

    assert await disp.dispatch(request) is None

    async def method1(param):
        return param

    disp.add(method1)

    request = json.dumps({
        'jsonrpc': '2.0',
        'id': 1,
        'method': 'method1',
        'params': ['param1'],
    })

    response, error_codes = await disp.dispatch(request)
    assert json.loads(response) == {
        'jsonrpc': '2.0',
        'id': 1,
        'result': 'param1',
    }

    async def method2():
        raise Exception('unhandled error')

    disp.add(method2)

    request = json.dumps({
        'jsonrpc': '2.0',
        'id': 1,
        'method': 'method2',
    })

    response, error_codes = await disp.dispatch(request)
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

    response, error_codes = await disp.dispatch(request)
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

    response, error_codes = await disp.dispatch('')
    assert json.loads(response) == {
        'jsonrpc': '2.0',
        'id': None,
        'error': {
            'code': -32700,
            'message': 'Parse error',
            'data': _,
        },
    }

    response, error_codes = await disp.dispatch('{}')
    assert json.loads(response) == {
        'jsonrpc': '2.0',
        'id': None,
        'error': {
            'code': -32600,
            'message': 'Invalid Request',
            'data': _,
        },
    }

    request = json.dumps([
        {
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'method',
        },
        {
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'method',
        },
    ])

    response, error_codes = await disp.dispatch(request)
    assert json.loads(response) == {
        'jsonrpc': '2.0',
        'id': None,
        'error': {
            'code': -32600,
            'message': 'Invalid Request',
            'data': 'request id duplicates found: 1',
        },
    }

    response, error_codes = await disp.dispatch(request)
    assert json.loads(response) == {
        'jsonrpc': '2.0',
        'id': None,
        'error': {
            'code': -32600,
            'message': 'Invalid Request',
            'data': 'request id duplicates found: 1',
        },
    }
