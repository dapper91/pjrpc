import json
import pytest

import xjsonrpc
from xjsonrpc.client.integrations.pytest import PjRpcMocker


class SyncClient:
    def __init__(self, endpoint):
        self._endpoint = endpoint

    def _request(self, data, is_notification=False, **kwargs):
        return json.dumps(xjsonrpc.Response(id='original_id', result='original_result').to_json())


@pytest.fixture
def endpoint():
    return 'endpoint'


@pytest.fixture
def cli(endpoint):
    return SyncClient(endpoint)


def test_context_manager(cli, endpoint):
    with PjRpcMocker('test_pytest_plugin.SyncClient._request') as mocker:
        mocker.add(endpoint, 'method', result='result')
        cli._request(json.dumps(xjsonrpc.Request(method='method').to_json()))

    assert mocker._patcher not in mocker._patcher._active_patches
    assert not mocker._matches
    assert not mocker._calls


def test_xjsonrpc_mocker_result_error_id(cli, endpoint):
    with PjRpcMocker('test_pytest_plugin.SyncClient._request') as mocker:
        mocker.add(endpoint, 'method1', result='result')
        response = xjsonrpc.Response.from_json(
            json.loads(
                cli._request(json.dumps(xjsonrpc.Request(method='method1').to_json())),
            ),
        )
        assert response.result == 'result'

        mocker.add(endpoint, 'method2', error=xjsonrpc.exc.JsonRpcError(code=1, message='message'))
        response = xjsonrpc.Response.from_json(
            json.loads(
                cli._request(json.dumps(xjsonrpc.Request(method='method2').to_json())),
            ),
        )

        assert response.error == xjsonrpc.exc.JsonRpcError(code=1, message='message')


def test_xjsonrpc_mocker_once_param(cli, endpoint):
    with PjRpcMocker('test_pytest_plugin.SyncClient._request', passthrough=True) as mocker:
        mocker.add(endpoint, 'method', result='result', once=True)
        response = xjsonrpc.Response.from_json(
            json.loads(
                cli._request(json.dumps(xjsonrpc.Request(method='method').to_json())),
            ),
        )
        assert response.result == 'result'

        response = xjsonrpc.Response.from_json(
            json.loads(
                cli._request(json.dumps(xjsonrpc.Request(method='method').to_json())),
            ),
        )
        assert response.result == 'original_result'


def test_xjsonrpc_mocker_round_robin(cli, endpoint):
    with PjRpcMocker('test_pytest_plugin.SyncClient._request') as mocker:
        mocker.add(endpoint, 'method', result='result1')
        mocker.add(endpoint, 'method', result='result2')

        response = xjsonrpc.Response.from_json(
            json.loads(
                cli._request(json.dumps(xjsonrpc.Request(method='method').to_json())),
            ),
        )
        assert response.result == 'result1'

        response = xjsonrpc.Response.from_json(
            json.loads(
                cli._request(json.dumps(xjsonrpc.Request(method='method').to_json())),
            ),
        )
        assert response.result == 'result2'

        response = xjsonrpc.Response.from_json(
            json.loads(
                cli._request(json.dumps(xjsonrpc.Request(method='method').to_json())),
            ),
        )
        assert response.result == 'result1'


def test_xjsonrpc_replace_remove(cli, endpoint):
    with PjRpcMocker('test_pytest_plugin.SyncClient._request', passthrough=True) as mocker:
        mocker.add(endpoint, 'method', result='result1')
        response = xjsonrpc.Response.from_json(
            json.loads(
                cli._request(json.dumps(xjsonrpc.Request(method='method').to_json())),
            ),
        )
        assert response.result == 'result1'

        mocker.replace(endpoint, 'method', result='result2')
        response = xjsonrpc.Response.from_json(
            json.loads(
                cli._request(json.dumps(xjsonrpc.Request(method='method').to_json())),
            ),
        )
        assert response.result == 'result2'

        mocker.remove(endpoint, 'method')
        response = xjsonrpc.Response.from_json(
            json.loads(
                cli._request(json.dumps(xjsonrpc.Request(method='method').to_json())),
            ),
        )
        assert response.result == 'original_result'


def test_xjsonrpc_mocker_calls(endpoint):
    cli1 = SyncClient('endpoint1')
    cli2 = SyncClient('endpoint2')

    with PjRpcMocker('test_pytest_plugin.SyncClient._request') as mocker:
        mocker.add('endpoint1', 'method1', result='result')
        mocker.add('endpoint1', 'method2', result='result')
        mocker.add('endpoint2', 'method1', result='result')

        cli1._request(json.dumps(xjsonrpc.Request(method='method1', params=[1, '2']).to_json()))
        cli1._request(json.dumps(xjsonrpc.Request(method='method1', params=[1, '2']).to_json()))
        cli1._request(json.dumps(xjsonrpc.Request(method='method2', params=[1, '2']).to_json()))
        cli2._request(json.dumps(xjsonrpc.Request(method='method1', params={'a': 1, 'b': '2'}).to_json()))

        assert mocker.calls['endpoint1'][('2.0', 'method1')].mock_calls == [((1, '2'), {}), ((1, '2'), {})]
        assert mocker.calls['endpoint1'][('2.0', 'method2')].mock_calls == [((1, '2'), {})]
        assert mocker.calls['endpoint2'][('2.0', 'method1')].mock_calls == [({'a': 1, 'b': '2'},)]


def test_xjsonrpc_mocker_callback(cli, endpoint):
    with PjRpcMocker('test_pytest_plugin.SyncClient._request') as mocker:
        def callback(**kwargs):
            assert kwargs == {'a': 1, 'b': '2'}
            return 'result'

        mocker.add(endpoint, 'method', callback=callback)

        response = xjsonrpc.Response.from_json(
            json.loads(
                cli._request(json.dumps(xjsonrpc.Request(method='method', params={'a': 1, 'b': '2'}).to_json())),
            ),
        )

        assert response.result == 'result'


def test_xjsonrpc_mocker_passthrough(cli, endpoint):
    with PjRpcMocker('test_pytest_plugin.SyncClient._request', passthrough=True) as mocker:
        mocker.add('other_endpoint', 'method', result='result')

        response = xjsonrpc.Response.from_json(
            json.loads(
                cli._request(json.dumps(xjsonrpc.Request(method='method2').to_json())),
            ),
        )

        assert response.result == 'original_result'


class AsyncClient:
    def __init__(self, endpoint):
        self._endpoint = endpoint

    async def _request(self, data, is_notification=False, **kwargs):
        return json.dumps(xjsonrpc.Response(id='original_id', result='original_result').to_json())


async def test_xjsonrpc_mocker_async(endpoint):
    cli = AsyncClient(endpoint)

    with PjRpcMocker('test_pytest_plugin.AsyncClient._request') as mocker:
        mocker.add(endpoint, 'method1', result='result1')
        mocker.add(endpoint, 'method2', result='result2')

        batch = xjsonrpc.BatchResponse.from_json(
            json.loads(
                await cli._request(
                    json.dumps(
                        xjsonrpc.BatchRequest(
                            xjsonrpc.Request(method='method1'),
                            xjsonrpc.Request(method='method2'),
                        ).to_json(),
                    ),
                ),
            ),
        )

        assert batch[0].result == 'result1'
        assert batch[1].result == 'result2'
