from unittest import mock

import pytest
from aiohttp import web

import pjrpc.server
from pjrpc.client.backend import aiohttp as async_client
from pjrpc.client.integrations.pytest import PjRpcAiohttpMocker
from pjrpc.server.integration import aiohttp as integration

methods = pjrpc.server.MethodRegistry()


@methods.add
async def div(a, b):
    cli = async_client.Client('http://127.0.0.2:8000/api/v1')
    return await cli.proxy.div(a, b)


@pytest.fixture
def http_app():
    return web.Application()


@pytest.fixture
def jsonrpc_app(http_app):
    jsonrpc_app = integration.Application('/api/v1', app=http_app)
    jsonrpc_app.dispatcher.add_methods(methods)

    return jsonrpc_app


async def test_pjrpc_server(aiohttp_client, http_app, jsonrpc_app):
    jsonrpc_cli = async_client.Client('/api/v1', session=await aiohttp_client(http_app))

    with PjRpcAiohttpMocker(passthrough=True) as mocker:
        mocker.add('http://127.0.0.2:8000/api/v1', 'div', result=2)
        result = await jsonrpc_cli.proxy.div(4, 2)
        assert result == 2

        localhost_calls = mocker.calls['http://127.0.0.2:8000/api/v1']
        assert localhost_calls[('2.0', 'div')].mock_calls == [mock.call(4, 2)]
