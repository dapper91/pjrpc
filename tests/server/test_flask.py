import flask
import pytest

from pjrpc.common import BatchRequest, Request, Response
from pjrpc.server import exceptions
from pjrpc.server.dispatcher import MethodRegistry
from pjrpc.server.integration import flask as integration
from tests.common import _


@pytest.fixture
def path():
    return '/test/path'


@pytest.fixture
def app():
    return flask.Flask(__name__)


@pytest.fixture
def json_rpc(app, path):
    json_rpc = integration.JsonRPC(path, http_app=app)

    return json_rpc


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
def test_request(app, json_rpc, path, mocker, request_id, params, result):
    method_name = 'test_method'
    mock = mocker.Mock(name=method_name, return_value=result)

    registry = MethodRegistry()
    registry.add_method(mock, method_name)
    json_rpc.add_methods(registry)

    with app.test_client() as cli:
        raw = cli.post(path, json=Request(method=method_name, params=params, id=request_id).to_json())
        assert raw.status_code == 200

        resp = Response.from_json(raw.json, error_cls=exceptions.JsonRpcError)

        if isinstance(params, dict):
            mock.assert_called_once_with(kwargs=params)
        else:
            mock.assert_called_once_with(args=params)

        assert resp.id == request_id
        assert resp.result == result


def test_notify(app, json_rpc, path, mocker):
    params = [1, 2]
    method_name = 'test_method'
    mock = mocker.Mock(name=method_name, return_value='result')

    registry = MethodRegistry()
    registry.add_method(mock, method_name)
    json_rpc.add_methods(registry)

    with app.test_client() as cli:
        raw = cli.post(path, json=Request(method=method_name, params=params).to_json())
        assert raw.status_code == 200
        assert raw.is_json is False
        assert raw.data == b''


def test_errors(app, json_rpc, path, mocker):
    request_id = 1
    params = (1, 2)
    method_name = 'test_method'

    def error_method(*args, **kwargs):
        raise exceptions.JsonRpcError(code=1, message='message')

    mock = mocker.Mock(name=method_name, side_effect=error_method)

    registry = MethodRegistry()
    registry.add_method(mock, method_name)
    json_rpc.add_methods(registry)

    with app.test_client() as cli:
        # method not found
        raw = cli.post(path, json=Request(method='unknown_method', params=params, id=request_id).to_json())
        assert raw.status_code == 200

        resp = Response.from_json(raw.json, error_cls=exceptions.JsonRpcError)
        assert resp.id is request_id
        assert resp.is_error is True
        assert resp.error == exceptions.MethodNotFoundError(data="method 'unknown_method' not found")

        # customer error
        raw = cli.post(path, json=Request(method=method_name, params=params, id=request_id).to_json())
        assert raw.status_code == 200

        resp = Response.from_json(raw.json, error_cls=exceptions.JsonRpcError)
        mock.assert_called_once_with(args=params)
        assert resp.id == request_id
        assert resp.is_error is True
        assert resp.error == exceptions.JsonRpcError(code=1, message='message')

        # content type error
        raw = cli.post(path, data='')
        assert raw.status_code == 415

        # malformed json
        raw = cli.post(path, headers={'Content-Type': 'application/json'}, data='')
        assert raw.status_code == 200
        resp = Response.from_json(raw.json, error_cls=exceptions.JsonRpcError)
        assert resp.id is None
        assert resp.is_error is True
        assert resp.error == exceptions.ParseError(data=_)


async def test_http_status(app, path):
    expected_http_status = 400
    json_rpc = integration.JsonRPC(path, http_app=app, status_by_error=lambda codes: expected_http_status)
    json_rpc.add_methods(MethodRegistry())

    with app.test_client() as cli:
        raw = cli.post(path, json=Request(method='unknown_method', id=1).to_json())
        assert raw.status_code == expected_http_status

        raw = cli.post(path, json=BatchRequest(Request(method='unknown_method', id=1)).to_json())
        assert raw.status_code == expected_http_status
