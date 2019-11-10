.. _testing:

Testing
=======


pytest
------

``pjrpc`` implements pytest plugin that simplifies JSON-RPC requests mocking.
Look at the following test example:

.. code-block:: python

    import pytest
    from unittest import mock

    import pjrpc
    from pjrpc.client.integrations.pytest import PjRpcAsyncMocker
    from pjrpc.client.backend import aiohttp as aiohttp_client


    async def test_using_fixture(pjrpc_aiohttp_mocker):
        client = aiohttp_client.Client('http://localhost/api/v1')

        pjrpc_aiohttp_mocker.add('http://localhost/api/v1', 'sum', result=2)
        result = await client.proxy.sum(1, 1)
        assert result == 2

        pjrpc_aiohttp_mocker.replace(
            'http://localhost/api/v1', 'sum', error=pjrpc.exc.JsonRpcError(code=1, message='error', data='oops')
        )
        with pytest.raises(pjrpc.exc.JsonRpcError) as exc_info:
            await client.proxy.sum(a=1, b=1)

        assert exc_info.type is pjrpc.exc.JsonRpcError
        assert exc_info.value.code == 1
        assert exc_info.value.message == 'error'
        assert exc_info.value.data == 'oops'

        sum_calls = pjrpc_aiohttp_mocker.calls[('http://localhost/api/v1', '2.0', 'sum')]
        assert sum_calls.call_count == 2
        assert sum_calls.mock_calls == [mock.call(1, 1), mock.call(a=1, b=1)]


    async def test_using_resource_manager():
        client = aiohttp_client.Client('http://localhost/api/v1')

        with PjRpcAsyncMocker() as mocker:
            mocker.add('http://localhost/api/v1', 'div', result=2)
            result = await client.proxy.div(4, 2)
            assert result == 2
            assert mocker.calls[('http://localhost/api/v1', '2.0', 'div')].mock_calls == [mock.call(4, 2)]



For testing server-side code you should use framework-dependant utils and fixtures. Since ``pjrpc`` may be easily
extended you are free from writing JSON-RPC protocol related code.


aiohttp
-------

Testing aiohttp server code is very straightforward:

.. code-block:: python

    import uuid

    from aiohttp import web

    import pjrpc.server
    from pjrpc.server.integration import aiohttp
    from pjrpc.client.backend import aiohttp as aiohttp_client

    methods = pjrpc.server.MethodRegistry()

    @methods.add
    async def sum(request: web.Request, a, b):
        return a + b

    app = aiohttp.Application('/api/v1')
    app.dispatcher.add_methods(methods)

    async def test_sum(aiohttp_client, loop):
        session = await aiohttp_client(app)
        client = aiohttp_client.Client('http://localhost/api/v1', session=session)

        result = await client.sum(a=1, b=1)
        assert result == 2


flask
-----

For flask it stays the same:

.. code-block:: python

    import uuid

    import flask

    from pjrpc.server.integration import flask as integration
    from pjrpc.client.backend import requests as pjrpc_client

    methods = pjrpc.server.MethodRegistry()

    @methods.add
    def sum(request: web.Request, a, b):
        return a + b

    app = flask.Flask(__name__)
    json_rpc = integration.JsonRPC('/api/v1')
    json_rpc.dispatcher.add_methods(methods)
    json_rpc.init_app(app)

    def test_sum():
        with app.test_client() as c:
            client = pjrpc_client.Client('http://localhost/api/v1', session=c)
            result = await client.sum(a=1, b=1)
            assert result == 2
