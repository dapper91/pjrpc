import pytest
import responses
from aioresponses import aioresponses

import pjrpc
from pjrpc.client import retry
from pjrpc.client.backend import aiohttp as aiohttp_backend
from pjrpc.client.backend import requests as requests_backend
from pjrpc.common import UNSET


@pytest.mark.parametrize(
    'strategy, expected',
    [
        (
            retry.PeriodicBackoff(attempts=5, interval=1.0, jitter=lambda: 0.1),
            (1.1, 1.1, 1.1, 1.1, 1.1),
        ),
        (
            retry.ExponentialBackoff(attempts=5, base=1.0, factor=2.0, max_value=10.0, jitter=lambda: -0.2),
            (0.8, 1.8, 3.8, 7.8, 10.0),
        ),
        (
            retry.FibonacciBackoff(attempts=5, multiplier=2, max_value=10.0),
            (2.0, 4.0, 6.0, 10.0, 10.0),
        ),
    ],
)
def test_retry_strategies(strategy, expected):
    assert tuple(strategy()) == expected


@pytest.mark.parametrize(
    'resp_code, resp_errors, retry_codes, retry_attempts, success',
    [
        (2001, 2, {2000, 2001}, 2, True),
        (2000, 2, {2000}, 2, True),
        (2000, 2, {2001}, 2, False),
        (2000, 1, {2000}, 2, True),
        (2000, 3, {2000}, 2, False),
        (2000, 1, {}, 2, False),
        (2000, 0, {}, 0, True),
    ],
)
async def test_async_client_retry_strategy_by_code(resp_code, resp_errors, retry_codes, retry_attempts, success):
    with aioresponses() as mock:
        test_url = 'http://test.com/api'
        expected_result = 'result'

        resp_success = dict(
            url=test_url,
            payload={"jsonrpc": "2.0", "result": expected_result, "id": 1},
        )
        resp_error = dict(
            url=test_url,
            payload={"jsonrpc": "2.0", "error": {"code": resp_code, "message": "error"}, "id": 1},
        )

        client = aiohttp_backend.Client(
            url=test_url,
            retry_strategy=retry.RetryStrategy(
                codes=retry_codes,
                backoff=retry.PeriodicBackoff(attempts=retry_attempts, interval=0.0),
            ),
        )

        for _ in range(resp_errors):
            mock.post(**resp_error)
        mock.post(**resp_success)

        if success:
            actual_result = await client.proxy.method()
            assert actual_result == expected_result
        else:
            with pytest.raises(pjrpc.exceptions.JsonRpcError) as err:
                await client.proxy.method()

            assert err.value.code == resp_code


@pytest.mark.parametrize(
    'resp_exc, resp_errors, retry_exc, retry_attempts, success',
    [
        (ConnectionError, 2, {TimeoutError, ConnectionError}, 2, True),
        (TimeoutError, 2, {TimeoutError}, 2, True),
        (TimeoutError, 2, {ConnectionError}, 2, False),
        (TimeoutError, 1, {TimeoutError}, 2, True),
        (TimeoutError, 3, {TimeoutError}, 2, False),
        (TimeoutError, 1, {}, 2, False),
        (TimeoutError, 0, {}, 0, True),
    ],
)
async def test_async_client_retry_strategy_by_exception(resp_exc, resp_errors, retry_exc, retry_attempts, success):
    with aioresponses() as mock:
        test_url = 'http://test.com/api'
        expected_result = 'result'

        resp_success = dict(
            url=test_url,
            payload={"jsonrpc": "2.0", "result": expected_result, "id": 1},
        )
        resp_error = dict(
            url=test_url,
            exception=resp_exc(),
        )

        client = aiohttp_backend.Client(
            url=test_url,
            retry_strategy=retry.RetryStrategy(
                exceptions=retry_exc,
                backoff=retry.PeriodicBackoff(attempts=retry_attempts, interval=0.0),
            ),
        )

        for _ in range(resp_errors):
            mock.post(**resp_error)
        mock.post(**resp_success)

        if success:
            actual_result = await client.proxy.method()
            assert actual_result == expected_result
        else:
            with pytest.raises(resp_exc):
                await client.proxy.method()


@pytest.mark.parametrize(
    'resp_code, resp_errors, retry_codes, retry_attempts, success',
    [
        (2001, 2, {2000, 2001}, 2, True),
        (2000, 2, {2000}, 2, True),
        (2000, 2, {2001}, 2, False),
        (2000, 1, {2000}, 2, True),
        (2000, 3, {2000}, 2, False),
        (2000, 1, {}, 2, False),
        (2000, 0, {}, 0, True),
    ],
)
@responses.activate
def test_client_retry_strategy_by_code(resp_code, resp_errors, retry_codes, retry_attempts, success):
    test_url = 'http://test.com/api'
    expected_result = 'result'

    resp_success = responses.Response(
        method=responses.POST,
        url=test_url,
        status=200,
        json={"jsonrpc": "2.0", "result": expected_result, "id": 1},
    )
    resp_error = responses.Response(
        method=responses.POST,
        url=test_url,
        status=200,
        json={"jsonrpc": "2.0", "error": {"code": resp_code, "message": "error"}, "id": 1},
    )

    client = requests_backend.Client(
        url=test_url,
        retry_strategy=retry.RetryStrategy(
            codes=retry_codes,
            backoff=retry.PeriodicBackoff(attempts=retry_attempts, interval=0.0),
        ),
    )

    for _ in range(resp_errors):
        responses.add(resp_error)
    responses.add(resp_success)

    if success:
        actual_result = client.proxy.method()
        assert actual_result == expected_result
    else:
        with pytest.raises(pjrpc.exceptions.JsonRpcError) as err:
            client.proxy.method()

        assert err.value.code == resp_code


@pytest.mark.parametrize(
    'resp_exc, resp_errors, retry_exc, retry_attempts, success',
    [
        (ConnectionError, 2, {TimeoutError, ConnectionError}, 2, True),
        (TimeoutError, 2, {TimeoutError}, 2, True),
        (TimeoutError, 2, {ConnectionError}, 2, False),
        (TimeoutError, 1, {TimeoutError}, 2, True),
        (TimeoutError, 3, {TimeoutError}, 2, False),
        (TimeoutError, 1, {}, 2, False),
        (TimeoutError, 0, {}, 0, True),
    ],
)
@responses.activate
def test_client_retry_strategy_by_exception(resp_exc, resp_errors, retry_exc, retry_attempts, success):
    test_url = 'http://test.com/api'
    expected_result = 'result'

    resp_success = responses.Response(
        method=responses.POST,
        url=test_url,
        status=200,
        json={"jsonrpc": "2.0", "result": expected_result, "id": 1},
    )
    resp_error = responses.Response(
        method=responses.POST,
        url=test_url,
        status=200,
        body=resp_exc(),
    )

    client = requests_backend.Client(
        url=test_url,
        retry_strategy=retry.RetryStrategy(
            exceptions=retry_exc,
            backoff=retry.PeriodicBackoff(attempts=retry_attempts, interval=0.0),
        ),
    )

    for _ in range(resp_errors):
        responses.add(resp_error)
    responses.add(resp_success)

    if success:
        actual_result = client.proxy.method()
        assert actual_result == expected_result
    else:
        with pytest.raises(resp_exc):
            client.proxy.method()


@responses.activate
def test_client_retry_strategy_by_code_and_exception():
    test_url = 'http://test.com/api'
    expected_result = 'result'

    client = requests_backend.Client(
        url=test_url,
        retry_strategy=retry.RetryStrategy(
            codes={2000},
            exceptions={TimeoutError},
            backoff=retry.PeriodicBackoff(attempts=2, interval=0.0),
        ),
    )

    responses.add(
        responses.Response(
            method=responses.POST,
            url=test_url,
            status=200,
            body=TimeoutError(),
        ),
    )
    responses.add(
        responses.Response(
            method=responses.POST,
            url=test_url,
            status=200,
            json={"jsonrpc": "2.0", "error": {"code": 2000, "message": "error"}, "id": 1},
        ),
    )
    responses.add(
        responses.Response(
            method=responses.POST,
            url=test_url,
            status=200,
            json={"jsonrpc": "2.0", "result": expected_result, "id": 1},
        ),
    )

    actual_result = client.proxy.method()
    assert actual_result == expected_result


@pytest.mark.parametrize(
    'resp_code, default_retry_codes, request_retry_codes, success',
    [
        (2001, None, None, False),
        (2001, {2001}, None, True),
        (2001, None, {2001}, True),
        (2001, {2001}, {2002}, False),
        (2001, {2002}, {2001}, True),
    ],
)
@responses.activate
def test_request_retry_strategy(resp_code, default_retry_codes, request_retry_codes, success):
    test_url = 'http://test.com/api'
    expected_result = 'result'

    resp_success = responses.Response(
        method=responses.POST,
        url=test_url,
        status=200,
        json={"jsonrpc": "2.0", "result": expected_result, "id": 1},
    )
    resp_error = responses.Response(
        method=responses.POST,
        url=test_url,
        status=200,
        json={"jsonrpc": "2.0", "error": {"code": resp_code, "message": "error"}, "id": 1},
    )

    default_retry_strategy = retry.RetryStrategy(
        codes=default_retry_codes,
        backoff=retry.PeriodicBackoff(attempts=1, interval=0.0),
    ) if default_retry_codes else None

    client = requests_backend.Client(url=test_url, retry_strategy=default_retry_strategy)

    responses.add(resp_error)
    responses.add(resp_success)

    request_retry_strategy = retry.RetryStrategy(
        codes=request_retry_codes,
        backoff=retry.PeriodicBackoff(attempts=1, interval=0.0),
    ) if request_retry_codes else UNSET

    actual_result = client.send(pjrpc.Request('method', id=1), _retry_strategy=request_retry_strategy)
    if success:
        assert actual_result == pjrpc.Response(id=1, result=expected_result)
    else:
        assert actual_result == pjrpc.Response(id=1, error=pjrpc.exc.JsonRpcError(code=resp_code, message="error"))
