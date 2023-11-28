import json

import pytest
import werkzeug

from pjrpc import exc
from pjrpc.common import v20
from pjrpc.server.integration import werkzeug as integration
from tests.common import _


@pytest.fixture
def path():
    return '/test/path'


@pytest.fixture
def json_rpc(path):
    return integration.JsonRPC(path)


@pytest.mark.parametrize(
    'request_id, params, result', [
        (
                1,
                (1, 1.1, 'a', {}, False),
                [1, 1.1, 'a', {}, False],
        ),
        (
                'abc',
                {'int': 1, 'float': 1.1, 'str': 'a', 'dict': {}, 'bool': False},
                {'int': 1, 'float': 1.1, 'str': 'a', 'dict': {}, 'bool': False},
        ),
    ],
)
def test_request(json_rpc, path, mocker, request_id, params, result):
    method_name = 'test_method'
    mock = mocker.Mock(name=method_name, return_value=result)

    json_rpc.dispatcher.add(mock, method_name)

    cli = werkzeug.test.Client(json_rpc)
    test_response = cli.post(
        path, json=v20.Request(method=method_name, params=params, id=request_id).to_json(),
    )
    if type(test_response) is tuple:  # werkzeug 1.0
        body_iter, code, header = test_response
        body = b''.join(body_iter)
    else:  # werkzeug >= 2.1
        body, code = (test_response.data, test_response.status)
    assert code == '200 OK'

    resp = v20.Response.from_json(json.loads(body))

    if isinstance(params, dict):
        mock.assert_called_once_with(kwargs=params)
    else:
        mock.assert_called_once_with(args=params)

    assert resp.id == request_id
    assert resp.result == result


def test_notify(json_rpc, path, mocker):
    params = [1, 2]
    method_name = 'test_method'
    mock = mocker.Mock(name=method_name, return_value='result')

    json_rpc.dispatcher.add(mock, method_name)

    cli = werkzeug.test.Client(json_rpc)
    test_response = cli.post(
        path, json=v20.Request(method=method_name, params=params).to_json(),
    )
    if type(test_response) is tuple:  # werkzeug 1.0
        body_iter, code, header = test_response
        body = b''.join(body_iter)
    else:  # werkzeug >= 2.1
        body, code = (test_response.data, test_response.status)
    assert code == '200 OK'
    assert body == b''


def test_errors(json_rpc, path, mocker):
    request_id = 1
    params = (1, 2)
    method_name = 'test_method'

    def error_method(*args, **kwargs):
        raise exc.JsonRpcError(code=1, message='message')

    mock = mocker.Mock(name=method_name, side_effect=error_method)

    json_rpc.dispatcher.add(mock, method_name)

    cli = werkzeug.test.Client(json_rpc)
    # method not found
    test_response = cli.post(
        path, json=v20.Request(method='unknown_method', params=params, id=request_id).to_json(),
    )
    if type(test_response) is tuple:  # werkzeug 1.0
        body_iter, code, header = test_response
        body = b''.join(body_iter)
    else:  # werkzeug >= 2.1
        body, code = (test_response.data, test_response.status)
    assert code == '200 OK'

    resp = v20.Response.from_json(json.loads(body))
    assert resp.id is request_id
    assert resp.is_error is True
    assert resp.error == exc.MethodNotFoundError(data="method 'unknown_method' not found")

    # customer error
    test_response = cli.post(
        path, json=v20.Request(method=method_name, params=params, id=request_id).to_json(),
    )
    if type(test_response) is tuple:  # werkzeug 1.0
        body_iter, code, header = test_response
        body = b''.join(body_iter)
    else:  # werkzeug >= 2.1
        body, code = (test_response.data, test_response.status)
    assert code == '200 OK'

    resp = v20.Response.from_json(json.loads(body))
    mock.assert_called_once_with(args=params)
    assert resp.id == request_id
    assert resp.is_error is True
    assert resp.error == exc.JsonRpcError(code=1, message='message')

    # malformed json
    test_response = cli.post(
        path, headers={'Content-Type': 'application/json'}, data='',
    )
    if type(test_response) is tuple:  # werkzeug 1.0
        body_iter, code, header = test_response
        body = b''.join(body_iter)
    else:
        body, code = (test_response.data, test_response.status)
    assert code == '200 OK'
    resp = v20.Response.from_json(json.loads(body))
    assert resp.id is None
    assert resp.is_error is True
    assert resp.error == exc.ParseError(data=_)
