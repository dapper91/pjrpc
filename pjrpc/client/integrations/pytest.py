"""
`pytest <https://docs.pytest.org/en/latest/>`_ client library integration.
Implements some utilities for mocking out ``pjrpc`` library clients.
"""

import asyncio
import collections
import functools as ft
import json
import sys
import unittest.mock
from typing import Any, Callable, Dict, Optional, Union

import pytest

import pjrpc
from pjrpc import Response
from pjrpc.common import UNSET, UnsetType

IS_GE_PY38 = sys.version_info >= (3, 8)


class Match:
    """
    Match object. Incorporates request matching information.
    """

    def __init__(
        self,
        endpoint: str,
        version: str,
        method_name: str,
        once: bool,
        callback: Optional[Callable],
        **response_data: Any,
    ):
        self.endpoint = endpoint
        self.version = version
        self.method_name = method_name
        self.once = once
        self.callback = callback
        self.response_data = response_data


class PjRpcMocker:
    """
    Synchronous JSON-RPC client mocker.

    :param target: method to be mocked
    :param mocker: mocking package
    :param passthrough: pass not mocked requests to the original method
    """

    def __init__(self, target, mocker=unittest.mock, passthrough: bool = False):
        self._target = target
        self._mocker = mocker
        self._patcher = None
        self._async_resp = False
        self._passthrough = passthrough

        self._matches: Dict = collections.defaultdict(lambda: collections.defaultdict(list))
        self._calls: Dict = collections.defaultdict(dict)

    @property
    def calls(self) -> Dict:
        """
        Dictionary of JSON-PRC method calls.
        """

        return self._calls

    def add(
        self,
        endpoint: str,
        method_name: str,
        result: UnsetType = UNSET,
        error: UnsetType = UNSET,
        id: Optional[Union[int, str]] = None,
        version: str = '2.0',
        once: bool = False,
        callback: Optional[Callable] = None,
    ) -> None:
        """
        Appends response patch. If the same method patch already exists they will be used in a round-robin way.

        :param endpoint: request endpoint
        :param method_name: method name
        :param result: patched result
        :param error: patched error
        :param id: patched request id
        :param version: patched request version
        :param once: if ``True`` the patch will be deleted after the first call
        :param callback: patched request callback
        """

        match = Match(endpoint, version, method_name, once, id=id, result=result, error=error, callback=callback)
        self._matches[endpoint][(version, method_name)].append(match)

    def replace(
        self,
        endpoint: str,
        method_name: str,
        result: UnsetType = UNSET,
        error: UnsetType = UNSET,
        id: Optional[Union[int, str]] = None,
        version: str = '2.0',
        once: bool = False,
        callback: Optional[Callable] = None,
        idx: int = 0,
    ):
        """
        Replaces a previously added response patch by a new one.

        :param endpoint: request endpoint
        :param method_name: method name
        :param result: patched result
        :param error: patched error
        :param id: patched request id
        :param version: patched request version
        :param once: if ``True`` the patch will be deleted after the first call
        :param callback: patched request callback
        :param idx: patch index (if there are more than one)
        """

        match = Match(endpoint, version, method_name, once, id=id, result=result, error=error, callback=callback)
        self._matches[endpoint][(version, method_name)][idx] = match

    def remove(self, endpoint: str, method_name: Optional[str] = None, version: str = '2.0'):
        """
        Removes a previously added response patch.

        :param endpoint: request endpoint
        :param method_name: method name
        :param version: JSON-RPC request version

        :returns: removed response patch
        """

        if method_name is None:
            result = self._matches.pop(endpoint)
        else:
            result = self._matches[endpoint].pop((version, method_name))

        self._cleanup_matches(endpoint, version, method_name)

        return result

    def reset(self) -> None:
        """
        Removes all added matches and reset call statistics.
        """

        self._matches.clear()
        for calls in self._calls.values():
            for stub in calls.values():
                stub.reset_mock()

        self._calls.clear()

    def start(self):
        """
        Activates a patcher.
        """

        self._patcher = self._mocker.patch(self._target, side_effect=self._on_request, autospec=True)

        result = self._patcher.start()
        if asyncio.iscoroutinefunction(self._patcher.temp_original):
            self._async_resp = True

        return result

    def stop(self) -> None:
        """
        Stop an active patcher.
        """

        self.reset()
        self._patcher.stop()

    def _cleanup_matches(self, endpoint: str, version: str = '2.0', method_name: Optional[str] = None) -> None:
        matches = self._matches[endpoint].get((version, method_name))

        if not matches:
            self._matches[endpoint].pop((version, method_name), None)
        if not self._matches[endpoint]:
            self._matches.pop(endpoint)

    def _on_request(self, origin_self: Any, request_text: str) -> str:
        endpoint = origin_self._endpoint
        matches = self._matches.get(endpoint)
        if matches is None:
            if self._passthrough:
                return self._patcher.temp_original(origin_self, request_text)
            else:
                raise ConnectionRefusedError()

        json_data = json.loads(request_text)

        if isinstance(json_data, (list, tuple)):
            response = pjrpc.BatchResponse()
            for request in pjrpc.BatchRequest.from_json(json_data):
                response.append(
                    self._match_request(endpoint, request.version, request.method, request.params, request.id),
                )

        else:
            request = pjrpc.Request.from_json(json_data)
            response = self._match_request(endpoint, request.version, request.method, request.params, request.id)

        if not IS_GE_PY38 and self._async_resp:
            async def wrapper():
                return json.dumps(response.to_json())
            return wrapper()
        else:
            return json.dumps(response.to_json())

    def _match_request(
        self,
        endpoint: str,
        version: str,
        method_name: str,
        params: Optional[Union[list, dict]],
        id: Optional[Union[int, str]],
    ) -> Response:
        matches = self._matches[endpoint].get((version, method_name))
        if matches is None:
            return pjrpc.Response(id=id, error=pjrpc.exc.MethodNotFoundError(data=method_name))

        match = matches.pop(0)
        if not match.once:
            matches.append(match)

        self._cleanup_matches(endpoint, version, method_name)

        stub = self.calls[endpoint].setdefault(
            (version, method_name),
            self._mocker.MagicMock(spec=lambda *args, **kwargs: None, name=f'{endpoint}:{version}:{method_name}'),
        )
        if isinstance(params, (list, tuple)):
            stub(*params)
        else:
            stub(**params)

        if match.callback:
            if isinstance(params, (list, tuple)):
                result = match.callback(*params)
            else:
                result = match.callback(**params)

            return pjrpc.Response(id=id, result=result)

        else:
            return pjrpc.Response(
                id=id or match.response_data['id'],
                result=match.response_data['result'],
                error=match.response_data['error'],
            )

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        self.reset()


# shortcuts
PjRpcRequestsMocker = ft.partial(PjRpcMocker, target='pjrpc.client.backend.requests.Client._request')
PjRpcAiohttpMocker = ft.partial(PjRpcMocker, target='pjrpc.client.backend.aiohttp.Client._request')


@pytest.fixture
def pjrpc_requests_mocker():
    """
    Requests client mocking fixture.
    """

    with PjRpcRequestsMocker() as mocker:
        yield mocker


@pytest.fixture
def pjrpc_aiohttp_mocker():
    """
    Aiohttp client mocking fixture.
    """

    with PjRpcAiohttpMocker() as mocker:
        yield mocker
