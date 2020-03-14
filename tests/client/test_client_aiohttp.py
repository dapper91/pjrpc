import json
import yarl
from aioresponses import aioresponses

import pjrpc
from pjrpc.client.backend import aiohttp as pjrpc_cli


# TODO refactor tests
async def test_call():
    test_url = 'http://test.com/api'

    with aioresponses() as m:
        m.post(
            test_url, repeat=True, status=200, payload={
                'jsonrpc': '2.0',
                'id': 1,
                'result': 'result',
            },
        )

        client = pjrpc_cli.Client(test_url)

        response = await client.send(pjrpc.Request('method', (1, 2), id=1))

        assert response.id == 1
        assert response.result == 'result'

        assert len(m.requests) == 1
        requests = m.requests[('POST', yarl.URL(test_url))]
        assert json.loads(requests[0].kwargs['data']) == {
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'method',
            'params': [1, 2],
        }

        result = await client.call('method', arg1=1, arg2=2)
        assert result == 'result'

        requests = m.requests[('POST', yarl.URL(test_url))]
        assert json.loads(requests[1].kwargs['data']) == {
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'method',
            'params': {'arg1': 1, 'arg2': 2},
        }

        result = await client('method', 1, 2)
        assert result == 'result'

        requests = m.requests[('POST', yarl.URL(test_url))]
        assert json.loads(requests[2].kwargs['data']) == {
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'method',
            'params': [1, 2],
        }

        result = await client.proxy.method(1, 2)
        assert result == 'result'

        requests = m.requests[('POST', yarl.URL(test_url))]
        assert json.loads(requests[3].kwargs['data']) == {
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'method',
            'params': [1, 2],
        }


async def test_notify():
    test_url = 'http://test.com/api'
    with aioresponses() as m:
        m.post(test_url, repeat=True, status=200, body='')

        client = pjrpc_cli.Client(test_url)

        response = await client.send(pjrpc.Request('method', params=[1, 2]))
        assert response is None
        requests = m.requests[('POST', yarl.URL(test_url))]
        assert json.loads(requests[0].kwargs['data']) == {
            'jsonrpc': '2.0',
            'method': 'method',
            'params': [1, 2],
        }

        response = await client.notify('method', a=1, b=2)
        assert response is None
        assert json.loads(requests[1].kwargs['data']) == {
            'jsonrpc': '2.0',
            'method': 'method',
            'params': {'a': 1, 'b': 2},
        }


async def test_batch():
    test_url = 'http://test.com/api'
    with aioresponses() as m:
        m.post(
            test_url, repeat=True, status=200, payload=[
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

        client = pjrpc_cli.Client(test_url)

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

        requests = m.requests[('POST', yarl.URL(test_url))]
        assert json.loads(requests[0].kwargs['data']) == [
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

        requests = m.requests[('POST', yarl.URL(test_url))]
        assert json.loads(requests[1].kwargs['data']) == [
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

        requests = m.requests[('POST', yarl.URL(test_url))]
        assert json.loads(requests[2].kwargs['data']) == [
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

        requests = m.requests[('POST', yarl.URL(test_url))]
        assert json.loads(requests[3].kwargs['data']) == [
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

        m.post(test_url, repeat=True, status=200)
        result = await client.batch.notify('method1', 1, 2).notify('method2', 2, 3).call()
        assert result is None

        requests = m.requests[('POST', yarl.URL(test_url))]
        assert json.loads(requests[4].kwargs['data']) == [
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


async def test_context_manager():
    test_url = 'http://test.com/api'
    with aioresponses() as m:
        m.post(
            test_url, repeat=True, status=200, payload={
                'jsonrpc': '2.0',
                'id': 1,
                'result': 'result',
            },
        )

        async with pjrpc_cli.Client(test_url) as client:
            response = await client.send(pjrpc.Request('method', (1, 2), id=1))

            assert response.id == 1
            assert response.result == 'result'
