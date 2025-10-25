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
