import json
from typing import NamedTuple

import pytest
import respx
from aioresponses import aioresponses

import pjrpc
from pjrpc.client.backend import aiohttp as aiohttp_backend
from pjrpc.client.backend import httpx as httpx_backend


class AioHttpMocker:

    class Request(NamedTuple):
        url: str
        content: str

    def __init__(self):
        self.mocker = aioresponses()

    def __enter__(self):
        self.mocker.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.mocker.__exit__(exc_type, exc_val, exc_tb)

    def mock(self, method=None, url=None, status=None, content=None, json=None):
        self.mocker.add(method=method, url=url, status=status, body=content, payload=json, repeat=True)

    @property
    def requests(self):
        return [
            self.Request(url=str(key[1]), content=call.kwargs['data'])
            for key, calls in self.mocker.requests.items()
            for call in calls
        ]


class RespxMocker(respx.MockRouter):

    def mock(self, method=None, url=None, status=None, content=None, json=None):
        route = self.route(method=method, url=url)
        route.respond(status_code=status, content=content, json=json)

    @property
    def requests(self):
        return [request for request, response in self.calls]


@pytest.mark.parametrize(
    'Client, mocker', [
        (aiohttp_backend.Client, AioHttpMocker),
        (httpx_backend.AsyncClient, RespxMocker),
    ],
)
async def test_call(Client, mocker):
    test_url = 'http://test.com/api'

    with mocker() as mock:
        mock.mock(
            'POST', test_url, status=200, json={
                'jsonrpc': '2.0',
                'id': 1,
                'result': 'result',
            },
        )

        client = Client(test_url)

        response = await client.send(pjrpc.Request('method', (1, 2), id=1))
        assert response.id == 1
        assert response.result == 'result'

        assert mock.requests[0].url == test_url
        assert json.loads(mock.requests[0].content) == {
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'method',
            'params': [1, 2],
        }

        result = await client.call('method', arg1=1, arg2=2)
        assert result == 'result'

        assert mock.requests[1].url == test_url
        assert json.loads(mock.requests[1].content) == {
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'method',
            'params': {'arg1': 1, 'arg2': 2},
        }

        result = await client('method', 1, 2)
        assert result == 'result'

        assert mock.requests[2].url == test_url
        assert json.loads(mock.requests[2].content) == {
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'method',
            'params': [1, 2],
        }

        result = await client.proxy.method(1, 2)
        assert result == 'result'

        assert mock.requests[3].url == test_url
        assert json.loads(mock.requests[3].content) == {
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'method',
            'params': [1, 2],
        }


@pytest.mark.parametrize(
    'Client, mocker', [
        (aiohttp_backend.Client, AioHttpMocker),
        (httpx_backend.AsyncClient, RespxMocker),
    ],
)
async def test_notify(Client, mocker):
    test_url = 'http://test.com/api'

    with mocker() as mock:
        mock.mock('POST', test_url, status=200, content=' ')

        client = Client(test_url)

        response = await client.send(pjrpc.Request('method', params=[1, 2]))
        assert response is None
        assert mock.requests[0].url == test_url
        assert json.loads(mock.requests[0].content) == {
            'jsonrpc': '2.0',
            'method': 'method',
            'params': [1, 2],
        }

        response = await client.notify('method', a=1, b=2)
        assert response is None
        assert mock.requests[1].url == test_url
        assert json.loads(mock.requests[1].content) == {
            'jsonrpc': '2.0',
            'method': 'method',
            'params': {'a': 1, 'b': 2},
        }


@pytest.mark.parametrize(
    'Client, mocker', [
        (aiohttp_backend.Client, AioHttpMocker),
        (httpx_backend.AsyncClient, RespxMocker),
    ],
)
async def test_batch(Client, mocker):
    test_url = 'http://test.com/api'

    with mocker() as mock:
        mock.mock(
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

        client = Client(test_url)

        result = await client.batch.send(
            pjrpc.BatchRequest(
                pjrpc.Request('method1', params=[1, 2], id=1),
                pjrpc.Request('method2', params=[2, 3], id=2),
                pjrpc.Request('method3', params=[3, 4]),
            ),
        )
        assert len(result) == 2
        assert result[0].id == 1
        assert result[0].result == 'result1'
        assert result[1].id == 2
        assert result[1].result == 2

        assert mock.requests[0].url == test_url
        assert json.loads(mock.requests[0].content) == [
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

        result = await client.batch[
            ('method1', 1, 2),
            ('method2', 2, 3),
        ]
        assert result == ('result1', 2)

        assert mock.requests[1].url == test_url
        assert json.loads(mock.requests[1].content) == [
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

        result = await client.batch('method1', 1, 2)('method2', 2, 3).call()
        assert result == ('result1', 2)

        assert mock.requests[2].url == test_url
        assert json.loads(mock.requests[2].content) == [
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

        result = await client.batch.proxy.method1(1, 2).method2(2, 3)()
        assert result == ('result1', 2)

        assert mock.requests[3].url == test_url
        assert json.loads(mock.requests[3].content) == [
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

    with mocker() as mock:
        mock.mock('POST', test_url, status=200, content=' ')
        result = await client.batch.notify('method1', 1, 2).notify('method2', 2, 3).call()
        assert result is None

        assert mock.requests[0].url == test_url
        assert json.loads(mock.requests[0].content) == [
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
        (aiohttp_backend.Client, AioHttpMocker),
        (httpx_backend.AsyncClient, RespxMocker),
    ],
)
async def test_context_manager(Client, mocker):
    test_url = 'http://test.com/api'

    with mocker() as mock:
        mock.mock(
            'POST', test_url, status=200, json={
                'jsonrpc': '2.0',
                'id': 1,
                'result': 'result',
            },
        )

        async with Client(test_url) as client:
            response = await client.send(pjrpc.Request('method', (1, 2), id=1))

            assert response.id == 1
            assert response.result == 'result'
