import json
import pytest

import pjrpc
from pjrpc.client.integrations.pytest import PjRpcMocker


class TestClient:
    def __init__(self, endpoint):
        self._endpoint = endpoint

    def _request(self, data, is_notification=False, **kwargs):
        return json.dumps(pjrpc.Response(id='original_id', result='original_result').to_json())


@pytest.fixture
def endpoint():
    return 'endpoint'


@pytest.fixture
def cli(endpoint):
    return TestClient(endpoint)


def test_context_manager(cli, endpoint):
    with PjRpcMocker('test_pytest_plugin.TestClient._request') as mocker:
        mocker.add(endpoint, 'method', result='result')
        cli._request(json.dumps(pjrpc.Request(method='method').to_json()))

    assert mocker._patcher not in mocker._patcher._active_patches
    assert not mocker._matches
    assert not mocker._calls


def test_pjrpc_mocker_result_error_id(cli, endpoint):
    with PjRpcMocker('test_pytest_plugin.TestClient._request') as mocker:
        mocker.add(endpoint, 'method1', result='result')
        response = pjrpc.Response.from_json(
            json.loads(
                cli._request(json.dumps(pjrpc.Request(method='method1').to_json())),
            ),
        )
        assert response.result == 'result'

        mocker.add(endpoint, 'method2', error=pjrpc.exc.JsonRpcError(code=1, message='message'))
        response = pjrpc.Response.from_json(
            json.loads(
                cli._request(json.dumps(pjrpc.Request(method='method2').to_json())),
            ),
        )

        assert response.error == pjrpc.exc.JsonRpcError(code=1, message='message')


def test_pjrpc_mocker_once_param(cli, endpoint):
    with PjRpcMocker('test_pytest_plugin.TestClient._request', passthrough=True) as mocker:
        mocker.add(endpoint, 'method', result='result', once=True)
        response = pjrpc.Response.from_json(
            json.loads(
                cli._request(json.dumps(pjrpc.Request(method='method').to_json())),
            ),
        )
        assert response.result == 'result'

        response = pjrpc.Response.from_json(
            json.loads(
                cli._request(json.dumps(pjrpc.Request(method='method').to_json())),
            ),
        )
        assert response.result == 'original_result'


def test_pjrpc_mocker_round_robin(cli, endpoint):
    with PjRpcMocker('test_pytest_plugin.TestClient._request') as mocker:
        mocker.add(endpoint, 'method', result='result1')
        mocker.add(endpoint, 'method', result='result2')

        response = pjrpc.Response.from_json(
            json.loads(
                cli._request(json.dumps(pjrpc.Request(method='method').to_json())),
            ),
        )
        assert response.result == 'result1'

        response = pjrpc.Response.from_json(
            json.loads(
                cli._request(json.dumps(pjrpc.Request(method='method').to_json())),
            ),
        )
        assert response.result == 'result2'

        response = pjrpc.Response.from_json(
            json.loads(
                cli._request(json.dumps(pjrpc.Request(method='method').to_json())),
            ),
        )
        assert response.result == 'result1'


def test_pjrpc_replace_remove(cli, endpoint):
    with PjRpcMocker('test_pytest_plugin.TestClient._request', passthrough=True) as mocker:
        mocker.add(endpoint, 'method', result='result1')
        response = pjrpc.Response.from_json(
            json.loads(
                cli._request(json.dumps(pjrpc.Request(method='method').to_json())),
            ),
        )
        assert response.result == 'result1'

        mocker.replace(endpoint, 'method', result='result2')
        response = pjrpc.Response.from_json(
            json.loads(
                cli._request(json.dumps(pjrpc.Request(method='method').to_json())),
            ),
        )
        assert response.result == 'result2'

        mocker.remove(endpoint, 'method')
        response = pjrpc.Response.from_json(
            json.loads(
                cli._request(json.dumps(pjrpc.Request(method='method').to_json())),
            ),
        )
        assert response.result == 'original_result'


def test_pjrpc_mocker_calls(endpoint):
    cli1 = TestClient('endpoint1')
    cli2 = TestClient('endpoint2')

    with PjRpcMocker('test_pytest_plugin.TestClient._request') as mocker:
        mocker.add('endpoint1', 'method1', result='result')
        mocker.add('endpoint1', 'method2', result='result')
        mocker.add('endpoint2', 'method1', result='result')

        cli1._request(json.dumps(pjrpc.Request(method='method1', params=[1, '2']).to_json()))
        cli1._request(json.dumps(pjrpc.Request(method='method1', params=[1, '2']).to_json()))
        cli1._request(json.dumps(pjrpc.Request(method='method2', params=[1, '2']).to_json()))
        cli2._request(json.dumps(pjrpc.Request(method='method1', params={'a': 1, 'b': '2'}).to_json()))

        assert mocker.calls['endpoint1'][('2.0', 'method1')].mock_calls == [((1, '2'), {}), ((1, '2'), {})]
        assert mocker.calls['endpoint1'][('2.0', 'method2')].mock_calls == [((1, '2'), {})]
        assert mocker.calls['endpoint2'][('2.0', 'method1')].mock_calls == [({'a': 1, 'b': '2'},)]


def test_pjrpc_mocker_callback(cli, endpoint):
    with PjRpcMocker('test_pytest_plugin.TestClient._request') as mocker:
        def callback(**kwargs):
            assert kwargs == {'a': 1, 'b': '2'}
            return 'result'

        mocker.add(endpoint, 'method', callback=callback)

        response = pjrpc.Response.from_json(
            json.loads(
                cli._request(json.dumps(pjrpc.Request(method='method', params={'a': 1, 'b': '2'}).to_json())),
            ),
        )

        assert response.result == 'result'


def test_pjrpc_mocker_passthrough(cli, endpoint):
    with PjRpcMocker('test_pytest_plugin.TestClient._request', passthrough=True) as mocker:
        mocker.add('other_endpoint', 'method', result='result')

        response = pjrpc.Response.from_json(
            json.loads(
                cli._request(json.dumps(pjrpc.Request(method='method2').to_json())),
            ),
        )

        assert response.result == 'original_result'


class TestAsyncClient:
    def __init__(self, endpoint):
        self._endpoint = endpoint

    async def _request(self, data, is_notification=False, **kwargs):
        return json.dumps(pjrpc.Response(id='original_id', result='original_result').to_json())


async def test_pjrpc_mocker_async(endpoint):
    cli = TestAsyncClient(endpoint)

    with PjRpcMocker('test_pytest_plugin.TestAsyncClient._request') as mocker:
        mocker.add(endpoint, 'method1', result='result1')
        mocker.add(endpoint, 'method2', result='result2')

        batch = pjrpc.BatchResponse.from_json(
            json.loads(
                await cli._request(
                    json.dumps(
                        pjrpc.BatchRequest(
                            pjrpc.Request(method='method1'),
                            pjrpc.Request(method='method2'),
                        ).to_json(),
                    ),
                ),
            ),
        )

        assert batch[0].result == 'result1'
        assert batch[1].result == 'result2'
