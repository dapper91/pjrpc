import pytest
from aiohttp import web

from pjrpc import exc
from pjrpc.common import v20
from pjrpc.server.integration import aiohttp as integration

from tests.common import _


@pytest.fixture
def path():
    return '/test/path'


@pytest.fixture
def json_rpc(path):
    json_rpc = integration.Application(path)

    return json_rpc


@pytest.mark.parametrize(
    'request_id, params, result', [
        (
                1,
                (1, 1.1, 'str', {}, False),
                [1, 1.1, 'str', {}, False],
        ),
        (
                'abc',
                {'int': 1, 'float': 1.1, 'str': 'str', 'dict': {}, 'bool': False},
                {'int': 1, 'float': 1.1, 'str': 'str', 'dict': {}, 'bool': False},
        ),
    ],
)
async def test_request(json_rpc, path, mocker, aiohttp_client, request_id, params, result):
    method_name = 'test_method'
    mock = mocker.Mock(name=method_name, return_value=result)

    json_rpc.dispatcher.add(mock, method_name)

    cli = await aiohttp_client(json_rpc.app)
    raw = await cli.post(path, json=v20.Request(method=method_name, params=params, id=request_id).to_json())
    assert raw.status == 200

    resp = v20.Response.from_json(await raw.json())

    if isinstance(params, dict):
        mock.assert_called_once_with(kwargs=params)
    else:
        mock.assert_called_once_with(args=params)

    assert resp.id == request_id
    assert resp.result == result


async def test_notify(json_rpc, path, mocker, aiohttp_client):
    params = [1, 2]
    method_name = 'test_method'
    mock = mocker.Mock(name=method_name, return_value='result')

    json_rpc.dispatcher.add(mock, method_name)

    cli = await aiohttp_client(json_rpc.app)
    raw = await cli.post(path, json=v20.Request(method=method_name, params=params).to_json())
    assert raw.status == 200
    assert raw.content_type != 'application/json'
    assert await raw.read() == b''


async def test_errors(json_rpc, path, mocker, aiohttp_client):
    request_id = 1
    params = (1, 2)
    method_name = 'test_method'

    def error_method(*args, **kwargs):
        raise exc.JsonRpcError(code=1, message='message')

    mock = mocker.Mock(name=method_name, side_effect=error_method)

    json_rpc.dispatcher.add(mock, method_name)

    cli = await aiohttp_client(json_rpc.app)
    # method not found
    raw = await cli.post(path, json=v20.Request(method='unknown_method', params=params, id=request_id).to_json())
    assert raw.status == 200

    resp = v20.Response.from_json(await raw.json())
    assert resp.id is request_id
    assert resp.is_error is True
    assert resp.error == exc.MethodNotFoundError(data="method 'unknown_method' not found")

    # customer error
    raw = await cli.post(path, json=v20.Request(method=method_name, params=params, id=request_id).to_json())
    assert raw.status == 200

    resp = v20.Response.from_json(await raw.json())
    mock.assert_called_once_with(args=params)
    assert resp.id == request_id
    assert resp.is_error is True
    assert resp.error == exc.JsonRpcError(code=1, message='message')

    # content type error
    raw = await cli.post(path, data='')
    assert raw.status == 415

    # malformed json
    raw = await cli.post(path, headers={'Content-Type': 'application/json'}, data='')
    assert raw.status == 200
    resp = v20.Response.from_json(await raw.json())
    assert resp.id is None
    assert resp.is_error is True
    assert resp.error == exc.ParseError(data=_)

    # decoding error
    raw = await cli.post(path, headers={'Content-Type': 'application/json'}, data=b'\xff')
    assert raw.status == 400


async def test_context(json_rpc, path, mocker, aiohttp_client):
    request_id = 1
    params = (1, 2)
    method_name = 'test_method'

    # test list parameters
    mock = mocker.Mock(name=method_name, return_value='result')

    json_rpc.dispatcher.add(mock, method_name, context='request')

    cli = await aiohttp_client(json_rpc.app)
    raw = await cli.post(path, json=v20.Request(method=method_name, params=params, id=request_id).to_json())
    assert raw.status == 200

    mock.assert_called_once()
    call_args = mock.call_args[1]
    context, args = call_args['request'], call_args['args']
    assert isinstance(context, web.Request)
    assert args == params

    # test dict parameters
    params = {'param1': 1, 'param2': 2}

    mock.reset_mock()

    cli = await aiohttp_client(json_rpc.app)
    raw = await cli.post(path, json=v20.Request(method=method_name, params=params, id=request_id).to_json())
    assert raw.status == 200

    mock.assert_called_once()
    call_args = mock.call_args[1]
    context, kwargs = call_args['request'], call_args['kwargs']
    assert isinstance(context, web.Request)
    assert kwargs == params
