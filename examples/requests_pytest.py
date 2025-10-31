from unittest import mock

import pytest

import pjrpc
from pjrpc.client.backend import requests as requests_client
from pjrpc.client.integrations.pytest_requests import PjRpcRequestsMocker


def test_using_fixture(pjrpc_requests_mocker):
    client = requests_client.Client('http://localhost/api/v1')

    pjrpc_requests_mocker.add('http://localhost/api/v1', 'sum', result=2)
    result = client.proxy.sum(1, 1)
    assert result == 2

    pjrpc_requests_mocker.replace(
        'http://localhost/api/v1',
        'sum',
        error=pjrpc.client.exceptions.JsonRpcError(code=1, message='error', data='oops'),
    )
    with pytest.raises(pjrpc.client.exceptions.JsonRpcError) as exc_info:
        client.proxy.sum(a=1, b=1)

    assert exc_info.type is pjrpc.client.exceptions.JsonRpcError
    assert exc_info.value.code == 1
    assert exc_info.value.message == 'error'
    assert exc_info.value.data == 'oops'

    localhost_calls = pjrpc_requests_mocker.calls['http://localhost/api/v1']
    assert localhost_calls[('2.0', 'sum')].call_count == 2
    assert localhost_calls[('2.0', 'sum')].mock_calls == [mock.call(1, 1), mock.call(a=1, b=1)]

    client = requests_client.Client('http://localhost/api/v2')
    with pytest.raises(ConnectionRefusedError):
        client.proxy.sum(1, 1)


def test_using_resource_manager():
    client = requests_client.Client('http://localhost/api/v1')

    with PjRpcRequestsMocker() as mocker:
        mocker.add('http://localhost/api/v1', 'mult', result=4)
        mocker.add('http://localhost/api/v1', 'div', callback=lambda a, b: a/b)

        with client.batch() as batch:
            batch.proxy.div(4, 2)
            batch.proxy.mult(2, 2)

        result = batch.get_results()
        assert result == [2, 4]

        localhost_calls = mocker.calls['http://localhost/api/v1']
        assert localhost_calls[('2.0', 'div')].mock_calls == [mock.call(4, 2)]
        assert localhost_calls[('2.0', 'mult')].mock_calls == [mock.call(2, 2)]

        with pytest.raises(pjrpc.client.exceptions.MethodNotFoundError):
            client.proxy.sub(4, 2)
