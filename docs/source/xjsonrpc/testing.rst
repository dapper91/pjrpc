.. _testing:

Testing
=======


pytest
------

``xjsonrpc`` implements pytest plugin that simplifies JSON-RPC requests mocking.
Look at the following test example:

.. code-block:: python

    import pytest
    from unittest import mock

    import xjsonrpc
    from xjsonrpc.client.integrations.pytest import PjRpcAiohttpMocker
    from xjsonrpc.client.backend import aiohttp as aiohttp_client


    async def test_using_fixture(xjsonrpc_aiohttp_mocker):
        client = aiohttp_client.Client('http://localhost/api/v1')

        xjsonrpc_aiohttp_mocker.add('http://localhost/api/v1', 'sum', result=2)
        result = await client.proxy.sum(1, 1)
        assert result == 2

        xjsonrpc_aiohttp_mocker.replace(
            'http://localhost/api/v1', 'sum', error=xjsonrpc.exc.JsonRpcError(code=1, message='error', data='oops')
        )
        with pytest.raises(xjsonrpc.exc.JsonRpcError) as exc_info:
            await client.proxy.sum(a=1, b=1)

        assert exc_info.type is xjsonrpc.exc.JsonRpcError
        assert exc_info.value.code == 1
        assert exc_info.value.message == 'error'
        assert exc_info.value.data == 'oops'

        localhost_calls = xjsonrpc_aiohttp_mocker.calls['http://localhost/api/v1']
        assert localhost_calls[('2.0', 'sum')].call_count == 2
        assert localhost_calls[('2.0', 'sum')].mock_calls == [mock.call(1, 1), mock.call(a=1, b=1)]


    async def test_using_resource_manager():
        client = aiohttp_client.Client('http://localhost/api/v1')

        with PjRpcAiohttpMocker() as mocker:
            mocker.add('http://localhost/api/v1', 'div', result=2)
            result = await client.proxy.div(4, 2)
            assert result == 2

            localhost_calls = mocker.calls['http://localhost/api/v1']
            assert localhost_calls[('2.0', 'div')].mock_calls == [mock.call(4, 2)]



For testing server-side code you should use framework-dependant utils and fixtures. Since ``xjsonrpc`` can be easily
extended you are free from writing JSON-RPC protocol related code.


aiohttp
-------

Testing aiohttp server code is very straightforward:

.. code-block:: python

    import uuid

    from aiohttp import web

    import xjsonrpc.server
    from xjsonrpc.server.integration import aiohttp
    from xjsonrpc.client.backend import aiohttp as xjsonrpc_aiohttp_client

    methods = xjsonrpc.server.MethodRegistry()

    @methods.add
    async def sum(request: web.Request, a, b):
        return a + b

    jsonrpc_app = aiohttp.Application('/api/v1')
    jsonrpc_app.dispatcher.add_methods(methods)

    async def test_sum(aiohttp_client, loop):
        session = await aiohttp_client(jsonrpc_app.app)
        client = xjsonrpc_aiohttp_client.Client('http://localhost/api/v1', session=session)

        result = await client.sum(a=1, b=1)
        assert result == 2


flask
-----

For flask it stays the same:

.. code-block:: python

    import uuid

    import flask

    from xjsonrpc.server.integration import flask as integration
    from xjsonrpc.client.backend import requests as xjsonrpc_client

    methods = xjsonrpc.server.MethodRegistry()

    @methods.add
    def sum(request: web.Request, a, b):
        return a + b

    app = flask.Flask(__name__)
    json_rpc = integration.JsonRPC('/api/v1')
    json_rpc.dispatcher.add_methods(methods)
    json_rpc.init_app(app)

    def test_sum():
        with app.test_client() as c:
            client = xjsonrpc_client.Client('http://localhost/api/v1', session=c)
            result = await client.sum(a=1, b=1)
            assert result == 2
