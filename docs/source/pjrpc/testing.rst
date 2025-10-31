.. _testing:

Testing
=======


pytest
------

``pjrpc`` implements pytest plugin that simplifies JSON-RPC requests mocking.
To install the plugin add the following line to your pytest configuration:

.. code-block:: python

    pytest_plugins = ("pjrpc.client.integrations.pytest_aiohttp", )

or

 .. code-block:: python

    pytest_plugins = ("pjrpc.client.integrations.pytest_requests", )

or export the environment variable ``PYTEST_PLUGINS=pjrpc.client.integrations.pytest_aiohttp``.
For more information `see <https://docs.pytest.org/en/latest/how-to/plugins.html#requiring-loading-plugins-in-a-test-module-or-conftest-file>`_.

Look at the following test example:

.. code-block:: python

    from unittest import mock

    import pytest

    import pjrpc
    from pjrpc.client.backend import aiohttp as aiohttp_client
    from pjrpc.client.integrations.pytest_aiohttp import PjRpcAiohttpMocker


    async def test_using_fixture(pjrpc_aiohttp_mocker):
        client = aiohttp_client.Client('http://localhost/api/v1')

        pjrpc_aiohttp_mocker.add('http://localhost/api/v1', 'sum', result=2)
        result = await client.proxy.sum(1, 1)
        assert result == 2

        pjrpc_aiohttp_mocker.replace(
            'http://localhost/api/v1', 'sum', error=pjrpc.client.exceptions.JsonRpcError(code=1, message='error', data='oops'),
        )
        with pytest.raises(pjrpc.client.exceptions.JsonRpcError) as exc_info:
            await client.proxy.sum(a=1, b=1)

        assert exc_info.type is pjrpc.client.exceptions.JsonRpcError
        assert exc_info.value.code == 1
        assert exc_info.value.message == 'error'
        assert exc_info.value.data == 'oops'

        localhost_calls = pjrpc_aiohttp_mocker.calls['http://localhost/api/v1']
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



For testing server-side code you should use framework-dependant utils and fixtures. Since ``pjrpc`` can be easily
extended you are free from writing JSON-RPC protocol related code.


aiohttp
-------

Testing aiohttp server code is very straightforward:

.. code-block:: python

    import pytest
    from aiohttp import web

    import pjrpc.server
    from pjrpc.client.backend import aiohttp as async_client
    from pjrpc.server.integration import aiohttp as integration

    methods = pjrpc.server.MethodRegistry()


    @methods.add()
    async def div(a: int, b: int) -> float:
        return a / b


    @pytest.fixture
    def http_app():
        return web.Application()


    @pytest.fixture
    def jsonrpc_app(http_app):
        jsonrpc_app = integration.Application('/api/v1', http_app=http_app)
        jsonrpc_app.add_methods(methods)

        return jsonrpc_app


    async def test_pjrpc_server(aiohttp_client, http_app, jsonrpc_app):
        jsonrpc_cli = async_client.Client('/api/v1', session=await aiohttp_client(http_app))

        result = await jsonrpc_cli.proxy.div(4, 2)
        assert result == 2

        result = await jsonrpc_cli.proxy.div(6, 2)
        assert result == 3


flask
-----

For flask it stays the same:

.. code-block:: python

    import flask.testing
    import pytest
    import werkzeug.test

    import pjrpc.server
    from pjrpc.client.backend import requests as client
    from pjrpc.client.integrations.pytest_requests import PjRpcRequestsMocker
    from pjrpc.server.integration import flask as integration

    methods = pjrpc.server.MethodRegistry()


    @methods.add()
    def div(a: int, b: int) -> float:
        return a / b


    @pytest.fixture()
    def http_app():
        return flask.Flask(__name__)


    @pytest.fixture
    def jsonrpc_app(http_app):
        json_rpc = integration.JsonRPC('/api/v1', http_app=http_app)
        json_rpc.add_methods(methods)

        return jsonrpc_app


    class Response(werkzeug.test.Response):
        def raise_for_status(self):
            if self.status_code >= 400:
                raise Exception('client response error')

        @property
        def text(self):
            return self.data.decode()


    @pytest.fixture()
    def app_client(http_app):
        return flask.testing.FlaskClient(http_app, Response)


    def test_pjrpc_server(http_app, jsonrpc_app, app_client):
        with PjRpcRequestsMocker(passthrough=True) as mocker:
            jsonrpc_cli = client.Client('/api/v1', session=app_client)

            mocker.add('http://127.0.0.2:8000/api/v1', 'div', result=2)
            result = jsonrpc_cli.proxy.div(4, 2)
            assert result == 2

            result = jsonrpc_cli.proxy.div(6, 2)
            assert result == 3
