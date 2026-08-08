import json
from typing import NamedTuple

import pytest
import respx
from aiointercept import aiointercept
from pytest_lazy_fixtures import lf

import pjrpc
from pjrpc.client.backend import aiohttp as aiohttp_backend
from pjrpc.client.backend import httpx as httpx_backend


class AioHttpMocker:

    class Request(NamedTuple):
        url: str
        content: str

    def __init__(self):
        self.mocker = aiointercept(mock_external_urls=True)

    async def __aenter__(self):
        await self.mocker.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.mocker.__aexit__(exc_type, exc_val, exc_tb)

    def mock(self, method=None, url=None, status=None, content=None, json=None):
        self.mocker.add(method=method, url=url, status=status, body=content, payload=json, repeat=True)

    @property
    def requests(self):
        return [
            self.Request(url=str(key[1]), content=call.kwargs['data'])
            for key, calls in self.mocker.requests.items()
            for call in calls
        ]


@pytest.fixture()
async def aiohttp_mocker():
    async with AioHttpMocker() as moker:
        yield moker


class RespxMocker(respx.MockRouter):

    def mock(self, method=None, url=None, status=None, content=None, json=None):
        route = self.route(method=method, url=url)
        route.respond(status_code=status, content=content, json=json)

    @property
    def requests(self):
        return [request for request, response in self.calls]


@pytest.fixture()
async def respx_mocker():
    async with RespxMocker() as moker:
        yield moker


@pytest.mark.parametrize(
    'Client, mocker', [
        (aiohttp_backend.Client, lf('aiohttp_mocker')),
        (httpx_backend.AsyncClient, lf('respx_mocker')),
    ],
)
async def test_call(Client, mocker):
    test_url = 'http://test.com/api'

    mocker.mock(
        'POST', test_url, status=200, json={
            'jsonrpc': '2.0',
            'id': 1,
            'result': 'result',
        },
    )

    async with Client(test_url) as client:
        response = await client.send(pjrpc.Request(method='method', params=(1, 2), id=1))
        assert response.id == 1
        assert response.result == 'result'

        assert mocker.requests[0].url == test_url
        assert json.loads(mocker.requests[0].content) == {
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'method',
            'params': [1, 2],
        }

        result = await client.call('method', arg1=1, arg2=2)
        assert result == 'result'

        assert mocker.requests[1].url == test_url
        assert json.loads(mocker.requests[1].content) == {
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'method',
            'params': {'arg1': 1, 'arg2': 2},
        }

        result = await client('method', 1, 2)
        assert result == 'result'

        assert mocker.requests[2].url == test_url
        assert json.loads(mocker.requests[2].content) == {
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'method',
            'params': [1, 2],
        }

        result = await client.proxy.method(1, 2)
        assert result == 'result'

        assert mocker.requests[3].url == test_url
        assert json.loads(mocker.requests[3].content) == {
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'method',
            'params': [1, 2],
        }


@pytest.mark.parametrize(
    'Client, mocker', [
        (aiohttp_backend.Client, lf('aiohttp_mocker')),
        (httpx_backend.AsyncClient, lf('respx_mocker')),
    ],
)
async def test_notify(Client, mocker):
    test_url = 'http://test.com/api'

    mocker.mock('POST', test_url, status=200, content=' ')

    async with Client(test_url) as client:
        response = await client.send(pjrpc.Request(method='method', params=[1, 2]))
        assert response is None
        assert mocker.requests[0].url == test_url
        assert json.loads(mocker.requests[0].content) == {
            'jsonrpc': '2.0',
            'method': 'method',
            'params': [1, 2],
        }

        response = await client.notify('method', a=1, b=2)
        assert response is None
        assert mocker.requests[1].url == test_url
        assert json.loads(mocker.requests[1].content) == {
            'jsonrpc': '2.0',
            'method': 'method',
            'params': {'a': 1, 'b': 2},
        }


@pytest.mark.parametrize(
    'Client, mocker', [
        (aiohttp_backend.Client, lf('aiohttp_mocker')),
        (httpx_backend.AsyncClient, lf('respx_mocker')),
    ],
)
async def test_batch(Client, mocker):
    test_url = 'http://test.com/api'

    mocker.mock(
        'POST', test_url, status=200, json=[
            {
                'jsonrpc': '2.0',
                'id': 1,
                'result': 'result1',
            },
            {
                'jsonrpc': '2.0',
                'id': 2,
                'result': 2,
            },
        ],
    )

    async with Client(test_url) as client:
        async with client.batch() as batch:
            batch.send(pjrpc.Request(method='method1', params=[1, 2], id=1))
            batch.send(pjrpc.Request(method='method2', params=[2, 3], id=2))
            batch.send(pjrpc.Request(method='method3', params=[3, 4]))

        result = batch.get_response()

        assert len(result) == 2
        assert result[0].id == 1
        assert result[0].result == 'result1'
        assert result[1].id == 2
        assert result[1].result == 2

        assert mocker.requests[0].url == test_url
        assert json.loads(mocker.requests[0].content) == [
            {
                'jsonrpc': '2.0',
                'id': 1,
                'method': 'method1',
                'params': [1, 2],
            },
            {
                'jsonrpc': '2.0',
                'id': 2,
                'method': 'method2',
                'params': [2, 3],
            },
            {
                'jsonrpc': '2.0',
                'method': 'method3',
                'params': [3, 4],
            },
        ]

        async with client.batch() as batch:
            batch.call('method1', 1, 2)
            batch.call('method2', 2, 3)

        result = batch.get_results()
        assert result == ['result1', 2]

        assert mocker.requests[1].url == test_url
        assert json.loads(mocker.requests[1].content) == [
            {
                'jsonrpc': '2.0',
                'id': 1,
                'method': 'method1',
                'params': [1, 2],
            },
            {
                'jsonrpc': '2.0',
                'id': 2,
                'method': 'method2',
                'params': [2, 3],
            },
        ]

        async with client.batch() as batch:
            batch('method1', 1, 2)
            batch('method2', 2, 3)

        result = batch.get_results()
        assert result == ['result1', 2]

        assert mocker.requests[2].url == test_url
        assert json.loads(mocker.requests[2].content) == [
            {
                'jsonrpc': '2.0',
                'id': 1,
                'method': 'method1',
                'params': [1, 2],
            },
            {
                'jsonrpc': '2.0',
                'id': 2,
                'method': 'method2',
                'params': [2, 3],
            },
        ]

        async with client.batch() as batch:
            batch.proxy.method1(1, 2)
            batch.proxy.method2(2, 3)

        result = batch.get_results()
        assert result == ['result1', 2]

        assert mocker.requests[3].url == test_url
        assert json.loads(mocker.requests[3].content) == [
            {
                'jsonrpc': '2.0',
                'id': 1,
                'method': 'method1',
                'params': [1, 2],
            },
            {
                'jsonrpc': '2.0',
                'id': 2,
                'method': 'method2',
                'params': [2, 3],
            },
        ]

    mocker.mock('POST', test_url, status=200, content=' ')

    async with Client(test_url) as client:
        async with client.batch() as batch:
            batch.notify('method1', 1, 2)
            batch.notify('method2', 2, 3)

        result = batch.get_response()
        assert result is None

        assert mocker.requests[4].url == test_url
        assert json.loads(mocker.requests[4].content) == [
            {
                'jsonrpc': '2.0',
                'method': 'method1',
                'params': [1, 2],
            },
            {
                'jsonrpc': '2.0',
                'method': 'method2',
                'params': [2, 3],
            },
        ]


@pytest.mark.parametrize(
    'Client, mocker', [
        (aiohttp_backend.Client, lf('aiohttp_mocker')),
        (httpx_backend.AsyncClient, lf('respx_mocker')),
    ],
)
async def test_context_manager(Client, mocker):
    test_url = 'http://test.com/api'

    mocker.mock(
        'POST', test_url, status=200, json={
            'jsonrpc': '2.0',
            'id': 1,
            'result': 'result',
        },
    )

    async with Client(test_url) as client:
        response = await client.send(pjrpc.Request(method='method', params=(1, 2), id=1))

        assert response.id == 1
        assert response.result == 'result'
