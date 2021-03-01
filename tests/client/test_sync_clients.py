import json

import pytest
import responses
import respx

import pjrpc
from pjrpc.client.backend import requests as requests_backend
from pjrpc.client.backend import httpx as httpx_backend


class ResponsesMocker(responses.RequestsMock):

    def mock(self, method=None, url=None, status=None, content=None, json=None):
        self.add(method=method, url=url, status=status, body=content, json=json)

    @property
    def requests(self):
        requests = []
        for request, response in self.calls:
            request.content = request.body
            requests.append(request)

        return requests


class RespxMocker(respx.MockRouter):

    def mock(self, method=None, url=None, status=None, content=None, json=None):
        route = self.route(method=method, url=url)
        route.respond(status_code=status, content=content, json=json)

    @property
    def requests(self):
        return [request for request, response in self.calls]


@pytest.mark.parametrize(
    'Client, mocker', [
        (requests_backend.Client, ResponsesMocker),
        (httpx_backend.Client, RespxMocker),
    ],
)
def test_call(Client, mocker):
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

        response = client.send(pjrpc.Request('method', (1, 2), id=1))
        assert response.id == 1
        assert response.result == 'result'

        assert mock.requests[0].url == test_url
        assert json.loads(mock.requests[0].content) == {
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'method',
            'params': [1, 2],
        }

        result = client.call('method', arg1=1, arg2=2)
        assert result == 'result'

        assert mock.requests[1].url == test_url
        assert json.loads(mock.requests[1].content) == {
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'method',
            'params': {'arg1': 1, 'arg2': 2},
        }

        result = client('method', 1, 2)
        assert result == 'result'

        assert mock.requests[2].url == test_url
        assert json.loads(mock.requests[2].content) == {
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'method',
            'params': [1, 2],
        }

        result = client.proxy.method(1, 2)
        assert result == 'result'

        assert mock.requests[3].url == test_url
        assert json.loads(mock.requests[3].content) == {
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'method',
            'params': [1, 2],
        }

        result = client.proxy.method(arg1=1, arg2=2)
        assert result == 'result'

        assert mock.requests[4].url == test_url
        assert json.loads(mock.requests[4].content) == {
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'method',
            'params': {'arg1': 1, 'arg2': 2},
        }


@pytest.mark.parametrize(
    'Client, mocker', [
        (requests_backend.Client, ResponsesMocker),
        (httpx_backend.Client, RespxMocker),
    ],
)
def test_notify(Client, mocker):
    test_url = 'http://test.com/api'

    with mocker() as mock:
        mock.mock('POST', test_url, status=200, content='')
        client = Client(test_url)

        response = client.send(pjrpc.Request('method', params=[1, 2]))
        assert response is None
        assert mock.requests[0].url == test_url
        assert json.loads(mock.requests[0].content) == {
            'jsonrpc': '2.0',
            'method': 'method',
            'params': [1, 2],
        }

        response = client.notify('method', 1, 2)
        assert response is None
        assert mock.requests[0].url == test_url
        assert json.loads(mock.requests[0].content) == {
            'jsonrpc': '2.0',
            'method': 'method',
            'params': [1, 2],
        }


@pytest.mark.parametrize(
    'Client, mocker', [
        (requests_backend.Client, ResponsesMocker),
        (httpx_backend.Client, RespxMocker),
    ],
)
def test_batch(Client, mocker):
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

        result = client.batch.send(
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

        result = client.batch[
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

        result = client.batch('method1', 1, 2)('method2', 2, 3).call()
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

        result = client.batch.proxy.method1(1, 2).method2(2, 3)()
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

        result = client.batch.send(
            pjrpc.BatchRequest(
                pjrpc.Request(method='method1', params=[1, 2], id=1),
                pjrpc.Request(method='method2', params=[2, 3], id=2),
            ),
        )
        assert result[0].id == 1
        assert result[0].result == 'result1'
        assert result[1].id == 2
        assert result[1].result == 2

        assert mock.requests[4].url == test_url
        assert json.loads(mock.requests[4].content) == [
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
        mock.mock('POST', test_url, status=200)
        result = client.batch.notify('method1', 1, 2).notify('method2', 2, 3).call()
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
        (requests_backend.Client, ResponsesMocker),
        (httpx_backend.Client, RespxMocker),
    ],
)
def test_error(Client, mocker):
    test_url = 'http://test.com/api'

    with mocker() as mock:
        mock.mock(
            'POST', test_url, status=200, json={
                'jsonrpc': '2.0',
                'id': 1,
                'error': {
                    'code': -32601,
                    'message': 'Method not found',
                },
            },
        )

        client = Client(test_url)

        with pytest.raises(pjrpc.exceptions.MethodNotFoundError):
            client('method', 1, 2)

        assert mock.requests[0].url == test_url
        assert json.loads(mock.requests[0].content) == {
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'method',
            'params': [1, 2],
        }

    with mocker() as mock:
        mock.mock(
            'POST', test_url, status=200, json={
                'jsonrpc': '2.0',
                'error': {
                    'code': -32600,
                    'message': 'Invalid request',
                },
            },
        )

        with pytest.raises(pjrpc.exceptions.InvalidRequestError):
            client.batch[('method', 'param')]

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
                    'id': 3,
                    'result': 2,
                },
            ],
        )

        client = Client(test_url)

        with pytest.raises(pjrpc.exceptions.IdentityError):
            client.batch[
                ('method1', 'param'),
                ('method2', 'param'),
            ]


@pytest.mark.parametrize(
    'Client, mocker', [
        (requests_backend.Client, ResponsesMocker),
        (httpx_backend.Client, RespxMocker),
    ],
)
def test_context_manager(Client, mocker):
    test_url = 'http://test.com/api'

    with mocker() as mock:
        mock.mock(
            'POST', test_url, status=200, json={
                'jsonrpc': '2.0',
                'id': 1,
                'result': 'result',
            },
        )

        with Client(test_url) as client:
            response = client.send(pjrpc.Request('method', (1, 2), id=1))
            assert response.id == 1
            assert response.result == 'result'
