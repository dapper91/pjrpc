import flask
import pytest

from pjrpc import exc
from pjrpc.common import v20
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
    json_rpc = integration.JsonRPC(path)
    json_rpc.init_app(app)

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

    json_rpc.dispatcher.add(mock, method_name)

    with app.test_client() as cli:
        raw = cli.post(path, json=v20.Request(method=method_name, params=params, id=request_id).to_json())
        assert raw.status_code == 200

        resp = v20.Response.from_json(raw.json)

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

    json_rpc.dispatcher.add(mock, method_name)

    with app.test_client() as cli:
        raw = cli.post(path, json=v20.Request(method=method_name, params=params).to_json())
        assert raw.status_code == 200
        assert raw.is_json is False
        assert raw.data == b''


def test_errors(app, json_rpc, path, mocker):
    request_id = 1
    params = (1, 2)
    method_name = 'test_method'

    def error_method(*args, **kwargs):
        raise exc.JsonRpcError(code=1, message='message')

    mock = mocker.Mock(name=method_name, side_effect=error_method)

    json_rpc.dispatcher.add(mock, method_name)

    with app.test_client() as cli:
        # method not found
        raw = cli.post(path, json=v20.Request(method='unknown_method', params=params, id=request_id).to_json())
        assert raw.status_code == 200

        resp = v20.Response.from_json(raw.json)
        assert resp.id is request_id
        assert resp.is_error is True
        assert resp.error == exc.MethodNotFoundError(data="method 'unknown_method' not found")

        # customer error
        raw = cli.post(path, json=v20.Request(method=method_name, params=params, id=request_id).to_json())
        assert raw.status_code == 200

        resp = v20.Response.from_json(raw.json)
        mock.assert_called_once_with(args=params)
        assert resp.id == request_id
        assert resp.is_error is True
        assert resp.error == exc.JsonRpcError(code=1, message='message')

        # content type error
        raw = cli.post(path, data='')
        assert raw.status_code == 415

        # malformed json
        raw = cli.post(path, headers={'Content-Type': 'application/json'}, data='')
        assert raw.status_code == 200
        resp = v20.Response.from_json(raw.json)
        assert resp.id is None
        assert resp.is_error is True
        assert resp.error == exc.ParseError(data=_)

        # decoding error
        raw = cli.post(path, headers={'Content-Type': 'application/json'}, data=b'\xff')
        assert raw.status_code == 400
