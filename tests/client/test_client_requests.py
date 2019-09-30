import json

import pytest
import responses

import pjrpc
from pjrpc.client.backend import requests as pjrpc_cli


@responses.activate
def test_call():
    test_url = 'http://test.com/api'
    responses.add(responses.POST, test_url, status=200, json={
        'jsonrpc': '2.0',
        'id': 1,
        'result': 'result',
    })

    client = pjrpc_cli.Client(test_url)

    response = client.send(pjrpc.Request('method', (1, 2), id=1))
    assert response.id == 1
    assert response.result == 'result'

    assert responses.calls[0].request.url == test_url
    assert json.loads(responses.calls[0].request.body) == {
        'jsonrpc': '2.0',
        'id': 1,
        'method': 'method',
        'params': [1, 2]
    }

    result = client.call('method', arg1=1, arg2=2)
    assert result == 'result'

    assert responses.calls[1].request.url == test_url
    assert json.loads(responses.calls[1].request.body) == {
        'jsonrpc': '2.0',
        'id': 1,
        'method': 'method',
        'params': {'arg1': 1, 'arg2': 2},
    }

    result = client('method', 1, 2)
    assert result == 'result'

    assert responses.calls[2].request.url == test_url
    assert json.loads(responses.calls[2].request.body) == {
        'jsonrpc': '2.0',
        'id': 1,
        'method': 'method',
        'params': [1, 2]
    }

    result = client.proxy.method(1, 2)
    assert result == 'result'

    assert responses.calls[3].request.url == test_url
    assert json.loads(responses.calls[3].request.body) == {
        'jsonrpc': '2.0',
        'id': 1,
        'method': 'method',
        'params': [1, 2]
    }

    result = client.proxy.method(arg1=1, arg2=2)
    assert result == 'result'

    assert responses.calls[4].request.url == test_url
    assert json.loads(responses.calls[4].request.body) == {
        'jsonrpc': '2.0',
        'id': 1,
        'method': 'method',
        'params': {'arg1': 1, 'arg2': 2},
    }


@responses.activate
def test_notify():
    test_url = 'http://test.com/api'
    responses.add(responses.POST, test_url, status=200, body='')
    client = pjrpc_cli.Client(test_url)

    response = client.notify('method', 1, 2)
    assert response is None

    assert responses.calls[0].request.url == test_url
    assert json.loads(responses.calls[0].request.body) == {
        'jsonrpc': '2.0',
        'id': None,
        'method': 'method',
        'params': [1, 2]
    }


@responses.activate
def test_batch():
    test_url = 'http://test.com/api'
    responses.add(responses.POST, test_url, status=200, json=[
        {
            'jsonrpc': '2.0',
            'id': 1,
            'result': 'result1',
        },
        {
            'jsonrpc': '2.0',
            'id': 2,
            'result': 2,
        }
    ])

    client = pjrpc_cli.Client(test_url)

    result = client.batch[
        ('method1', 1, 2),
        ('method2', 2, 3),
    ]
    assert result == ('result1', 2)

    assert responses.calls[0].request.url == test_url
    assert json.loads(responses.calls[0].request.body) == [
        {
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'method1',
            'params': [1, 2]
        },
        {
            'jsonrpc': '2.0',
            'id': 2,
            'method': 'method2',
            'params': [2, 3]
        }
    ]

    result = client.batch('method1', 1, 2)('method2', 2, 3).call()
    assert result == ('result1', 2)

    assert responses.calls[1].request.url == test_url
    assert json.loads(responses.calls[1].request.body) == [
        {
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'method1',
            'params': [1, 2]
        },
        {
            'jsonrpc': '2.0',
            'id': 2,
            'method': 'method2',
            'params': [2, 3]
        }
    ]

    result = client.batch.proxy.method1(1, 2).method2(2, 3)()
    assert result == ('result1', 2)

    assert responses.calls[2].request.url == test_url
    assert json.loads(responses.calls[2].request.body) == [
        {
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'method1',
            'params': [1, 2]
        },
        {
            'jsonrpc': '2.0',
            'id': 2,
            'method': 'method2',
            'params': [2, 3]
        }
    ]


@responses.activate
def test_error():
    test_url = 'http://test.com/api'
    responses.add(responses.POST, test_url, status=200, json={
        'jsonrpc': '2.0',
        'id': 1,
        'error': {
            'code': -32601,
            'message': 'Method not found'
        },
    })

    client = pjrpc_cli.Client(test_url)

    with pytest.raises(pjrpc.exceptions.MethodNotFoundError):
        client('method', 1, 2)

    assert responses.calls[0].request.url == test_url
    assert json.loads(responses.calls[0].request.body) == {
        'jsonrpc': '2.0',
        'id': 1,
        'method': 'method',
        'params': [1, 2]
    }
