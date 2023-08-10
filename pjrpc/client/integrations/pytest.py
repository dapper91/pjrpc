"""
`pytest <https://docs.pytest.org/en/latest/>`_ client library integration.
Implements some utilities for mocking out ``pjrpc`` library clients.
"""

import asyncio
import collections
import functools as ft
import json
import unittest.mock
from types import ModuleType
from typing import Any, Callable, Dict, Generator, List, Optional, Tuple, Union

import pytest

import pjrpc
from pjrpc import Response
from pjrpc.common import UNSET, MaybeSet
from pjrpc.common.typedefs import JsonRpcParams, JsonRpcRequestId

CallType = Dict[Tuple[str, str], unittest.mock.Mock]
MatchType = Dict[Tuple[str, str], List['Match']]


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
        callback: Optional[Callable[..., Any]],
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

    def __init__(self, target: str, mocker: ModuleType = unittest.mock, passthrough: bool = False):
        self._target = target
        self._mocker = mocker
        self._patcher: Optional[Any] = None
        self._async_resp = False
        self._passthrough = passthrough

        self._matches: Dict[str, MatchType] = collections.defaultdict(lambda: collections.defaultdict(list))
        self._calls: Dict[str, CallType] = collections.defaultdict(dict)

    @property
    def calls(self) -> Dict[str, CallType]:
        """
        Dictionary of JSON-PRC method calls.
        """

        return self._calls

    def add(
        self,
        endpoint: str,
        method_name: str,
        result: MaybeSet[Any] = UNSET,
        error: MaybeSet[Any] = UNSET,
        id: Optional[JsonRpcRequestId] = None,
        version: str = '2.0',
        once: bool = False,
        callback: Optional[Callable[..., Any]] = None,
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
        result: MaybeSet[Any] = UNSET,
        error: MaybeSet[Any] = UNSET,
        id: Optional[JsonRpcRequestId] = None,
        version: str = '2.0',
        once: bool = False,
        callback: Optional[Callable[..., Any]] = None,
        idx: int = 0,
    ) -> None:
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

    def remove(
        self,
        endpoint: str,
        method_name: Optional[str] = None,
        version: str = '2.0',
    ) -> Union[MatchType, List[Match]]:
        """
        Removes a previously added response patch.

        :param endpoint: request endpoint
        :param method_name: method name
        :param version: JSON-RPC request version

        :returns: removed response patch
        """

        result: Union[MatchType, List[Match]]
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

    def start(self) -> Any:
        """
        Activates a patcher.
        """

        patcher = self._mocker.patch(self._target)
        with patcher:
            if asyncio.iscoroutinefunction(patcher.temp_original):
                self._async_resp = True

        side_effect: Callable[..., Any]
        if self._async_resp:
            async def side_effect(*args: Any, **kwargs: Any) -> str:
                return await self._on_request(*args, **kwargs)
        else:
            def side_effect(*args: Any, **kwargs: Any) -> str:
                return self._on_request(*args, **kwargs)

        self._patcher = self._mocker.patch(self._target, side_effect=side_effect, autospec=True)

        assert self._patcher is not None
        return self._patcher.start()

    def stop(self) -> None:
        """
        Stop an active patcher.
        """

        assert self._patcher is not None, 'mocker is not started'

        self.reset()
        self._patcher.stop()

    def _cleanup_matches(self, endpoint: str, version: str = '2.0', method_name: Optional[str] = None) -> None:
        matches: Optional[Union[MatchType, List[Match]]]
        if method_name is not None:
            matches = self._matches[endpoint].get((version, method_name))
        else:
            matches = self._matches[endpoint]

        if not matches and method_name:
            self._matches[endpoint].pop((version, method_name), None)
        if not self._matches[endpoint]:
            self._matches.pop(endpoint)

    def _on_request(self, origin_self: Any, request_text: str, is_notification: bool = False, **kwargs: Any) -> Any:
        assert self._patcher is not None, 'mocker is not started'

        endpoint = origin_self._endpoint
        matches = self._matches.get(endpoint)
        if matches is None:
            if self._passthrough:
                return self._patcher.temp_original(origin_self, request_text, is_notification, **kwargs)
            else:
                raise ConnectionRefusedError()

        json_data = json.loads(request_text)

        response: Union[pjrpc.BatchResponse, pjrpc.Response]
        if isinstance(json_data, (list, tuple)):
            response = pjrpc.BatchResponse()
            for request in pjrpc.BatchRequest.from_json(json_data):
                response.append(
                    self._match_request(endpoint, request.version, request.method, request.params, request.id),
                )

        else:
            request = pjrpc.Request.from_json(json_data)
            response = self._match_request(endpoint, request.version, request.method, request.params, request.id)

        if self._async_resp:
            async def wrapper() -> str:
                return json.dumps(response.to_json())
            return wrapper()
        else:
            return json.dumps(response.to_json())

    def _match_request(
        self,
        endpoint: str,
        version: str,
        method_name: str,
        params: Optional[JsonRpcParams],
        id: Optional[JsonRpcRequestId],
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
        elif isinstance(params, dict):
            stub(**params)
        else:
            stub(params)

        if match.callback:
            if isinstance(params, (list, tuple)):
                result = match.callback(*params)
            elif isinstance(params, dict):
                result = match.callback(**params)
            else:
                result = match.callback(params)

            return pjrpc.Response(id=id, result=result)

        else:
            return pjrpc.Response(
                id=id or match.response_data['id'],
                result=match.response_data['result'],
                error=match.response_data['error'],
            )

    def __enter__(self) -> 'PjRpcMocker':
        self.start()
        return self

    def __exit__(self, *args: Any) -> None:
        self.stop()
        self.reset()


# shortcuts
PjRpcRequestsMocker = ft.partial(PjRpcMocker, target='pjrpc.client.backend.requests.Client._request')
PjRpcAiohttpMocker = ft.partial(PjRpcMocker, target='pjrpc.client.backend.aiohttp.Client._request')


@pytest.fixture
def pjrpc_requests_mocker() -> Generator[PjRpcMocker, None, None]:
    """
    Requests client mocking fixture.
    """

    with PjRpcRequestsMocker() as mocker:
        yield mocker


@pytest.fixture
def pjrpc_aiohttp_mocker() -> Generator[PjRpcMocker, None, None]:
    """
    Aiohttp client mocking fixture.
    """

    with PjRpcAiohttpMocker() as mocker:
        yield mocker
