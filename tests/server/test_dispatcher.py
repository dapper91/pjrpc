import json
from pjrpc.server import dispatcher, Method, ViewMixin

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


async def test_method_registry_view():
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

    assert json.loads(disp.dispatch(request)) == {
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

    assert json.loads(disp.dispatch(request)) == {
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

    assert json.loads(disp.dispatch(request)) == {
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

    assert json.loads(disp.dispatch(request)) == [
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

    assert json.loads(disp.dispatch('')) == {
        'jsonrpc': '2.0',
        'id': None,
        'error': {
            'code': -32700,
            'message': 'Parse error',
            'data': _,
        },
    }

    assert json.loads(disp.dispatch('{}')) == {
        'jsonrpc': '2.0',
        'id': None,
        'error': {
            'code': -32600,
            'message': 'Invalid Request',
            'data': _,
        },
    }

    assert json.loads(disp.dispatch('[]')) == {
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

    assert json.loads(disp.dispatch(request)) == {
        'jsonrpc': '2.0',
        'id': None,
        'error': {
            'code': -32600,
            'message': 'Invalid Request',
            'data': 'request id duplicates found: 1',
        },
    }

    assert json.loads(disp.dispatch(request)) == {
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

    assert json.loads(await disp.dispatch(request)) == {
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

    assert json.loads(await disp.dispatch(request)) == {
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

    assert json.loads(await disp.dispatch(request)) == {
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

    assert json.loads(await disp.dispatch(request)) == [
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

    assert json.loads(await disp.dispatch('')) == {
        'jsonrpc': '2.0',
        'id': None,
        'error': {
            'code': -32700,
            'message': 'Parse error',
            'data': _,
        },
    }

    assert json.loads(await disp.dispatch('{}')) == {
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

    assert json.loads(await disp.dispatch(request)) == {
        'jsonrpc': '2.0',
        'id': None,
        'error': {
            'code': -32600,
            'message': 'Invalid Request',
            'data': 'request id duplicates found: 1',
        },
    }

    assert json.loads(await disp.dispatch(request)) == {
        'jsonrpc': '2.0',
        'id': None,
        'error': {
            'code': -32600,
            'message': 'Invalid Request',
            'data': 'request id duplicates found: 1',
        },
    }
