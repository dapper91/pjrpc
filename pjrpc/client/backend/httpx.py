import json
import typing
from typing import Any, Callable, Generator, Iterable, Mapping, Optional, Sequence, TypedDict, Union

import httpx

import pjrpc
from pjrpc.client import AbstractAsyncClient, AbstractClient, AsyncMiddleware, Middleware
from pjrpc.common import AbstractRequest, AbstractResponse, BatchRequest, BatchResponse, JSONEncoder, JsonRpcError
from pjrpc.common import Request, Response, generators
from pjrpc.common.typedefs import JsonRpcRequestIdT


class RequestArgs(TypedDict, total=False):
    headers: Union[Mapping[str, str], Sequence[tuple[str, str]]]
    cookies: httpx._types.CookieTypes
    auth: Union[httpx._types.AuthTypes, httpx._client.UseClientDefault]
    follow_redirects: Union[bool, httpx._client.UseClientDefault]
    timeout: Union[httpx._types.TimeoutTypes, httpx._client.UseClientDefault]
    extensions: httpx._types.RequestExtensions


class Client(AbstractClient):
    """
    `httpx <https://www.python-httpx.org/>`_ library sync client backend.

    :param url: url to be used as JSON-RPC endpoint.
    :param http_client: custom client to be used instead of :py:class:`httpx.Client`
    :param raise_for_status: should `ClientResponse.raise_for_status()` be called automatically
    :param id_gen_impl: identifier generator
    :param error_cls: JSON-RPC error base class
    :param json_loader: json loader
    :param json_dumper: json dumper
    :param json_encoder: json encoder
    :param json_decoder: json decoder
    """

    def __init__(
        self,
        url: str,
        *,
        http_client: Optional[httpx.Client] = None,
        raise_for_status: bool = True,
        id_gen_impl: Callable[..., Generator[JsonRpcRequestIdT, None, None]] = generators.sequential,
        error_cls: type[JsonRpcError] = JsonRpcError,
        json_loader: Callable[..., Any] = json.loads,
        json_dumper: Callable[..., str] = json.dumps,
        json_encoder: type[JSONEncoder] = JSONEncoder,
        json_decoder: Optional[json.JSONDecoder] = None,
        middlewares: Iterable[Middleware] = (),
    ):
        super().__init__(
            id_gen_impl=id_gen_impl,
            error_cls=error_cls,
            json_loader=json_loader,
            json_dumper=json_dumper,
            json_encoder=json_encoder,
            json_decoder=json_decoder,
            middlewares=middlewares,
        )
        self._endpoint = url
        self._http_client = http_client or httpx.Client()
        self._owned_http_client = http_client is None
        self._raise_for_status = raise_for_status

    @typing.overload
    def send(self, request: Request, **kwargs: Any) -> Optional[Response]:
        ...

    @typing.overload
    def send(self, request: BatchRequest, **kwargs: Any) -> Optional[BatchResponse]:
        ...

    def send(self, request: AbstractRequest, **kwargs: Any) -> Optional[AbstractResponse]:
        """
        Sends a JSON-RPC request.

        :param request: request instance
        :param kwargs: additional client request argument
        :returns: response instance or None if the request is a notification
        """

        return self._send(request, kwargs)

    def _request(
        self,
        request_text: str,
        is_notification: bool,
        request_kwargs: Mapping[str, Any],
    ) -> Optional[str]:
        """
        Sends a JSON-RPC request.

        :param request_text: request text
        :param is_notification: is the request a notification
        :param request_kwargs: additional client request argument
        :returns: response text
        """

        request_kwargs = typing.cast(RequestArgs, request_kwargs)

        request_kwargs['headers'] = headers = dict(request_kwargs.get('headers', {}))
        headers['Content-Type'] = self._request_content_type

        resp = self._http_client.post(self._endpoint, content=request_text, **request_kwargs)
        if self._raise_for_status:
            resp.raise_for_status()
        if is_notification:
            return None

        response_text = resp.text
        content_type = resp.headers.get('Content-Type', '')
        if response_text and content_type.split(';')[0] not in self._response_content_types:
            raise pjrpc.exc.DeserializationError(f"unexpected response content type: {content_type}")

        return response_text

    def close(self) -> None:
        """
        Closes the current http session.
        """

        if self._owned_http_client:
            self._http_client.close()

    def __enter__(self) -> 'Client':
        if self._owned_http_client:
            self._http_client.__enter__()

        return self

    def __exit__(self, *args: Any) -> None:
        if self._owned_http_client:
            self._http_client.__exit__(*args)


class AsyncClient(AbstractAsyncClient):
    """
    `httpx <https://www.python-httpx.org/>`_ library async client backend.

    :param url: url to be used as JSON-RPC endpoint.
    :param http_client: custom client to be used instead of :py:class:`httpx.AsyncClient`
    :param raise_for_status: should `ClientResponse.raise_for_status()` be called automatically
    :param id_gen_impl: identifier generator
    :param error_cls: JSON-RPC error base class
    :param json_loader: json loader
    :param json_dumper: json dumper
    :param json_encoder: json encoder
    :param json_decoder: json decoder
    """

    def __init__(
        self,
        url: str,
        *,
        http_client: Optional[httpx.AsyncClient] = None,
        raise_for_status: bool = True,
        id_gen_impl: Callable[..., Generator[JsonRpcRequestIdT, None, None]] = generators.sequential,
        error_cls: type[JsonRpcError] = JsonRpcError,
        json_loader: Callable[..., Any] = json.loads,
        json_dumper: Callable[..., str] = json.dumps,
        json_encoder: type[JSONEncoder] = JSONEncoder,
        json_decoder: Optional[json.JSONDecoder] = None,
        middlewares: Iterable[AsyncMiddleware] = (),
    ):
        super().__init__(
            id_gen_impl=id_gen_impl,
            error_cls=error_cls,
            json_loader=json_loader,
            json_dumper=json_dumper,
            json_encoder=json_encoder,
            json_decoder=json_decoder,
            middlewares=middlewares,
        )
        self._endpoint = url
        self._http_client = http_client or httpx.AsyncClient()
        self._owned_http_client = http_client is None
        self._raise_for_status = raise_for_status

    @typing.overload
    async def send(self, request: Request, **kwargs: Any) -> Optional[Response]:
        ...

    @typing.overload
    async def send(self, request: BatchRequest, **kwargs: Any) -> Optional[BatchResponse]:
        ...

    async def send(self, request: AbstractRequest, **kwargs: Any) -> Optional[AbstractResponse]:
        """
        Sends a JSON-RPC request.

        :param request: request instance
        :param kwargs: additional client request argument
        :returns: response instance or None if the request is a notification
        """

        return await self._send(request, kwargs)

    async def _request(
        self,
        request_text: str,
        is_notification: bool,
        request_kwargs: Mapping[str, Any],
    ) -> Optional[str]:
        """
        Sends a JSON-RPC request.

        :param request_text: request text
        :param is_notification: is the request a notification
        :param request_kwargs: additional client request argument
        :returns: response text
        """

        request_kwargs = typing.cast(RequestArgs, request_kwargs)

        request_kwargs['headers'] = headers = dict(request_kwargs.get('headers', {}))
        headers['Content-Type'] = self._request_content_type

        resp = await self._http_client.post(self._endpoint, content=request_text, **request_kwargs)
        if self._raise_for_status:
            resp.raise_for_status()

        response_buff: list[str] = []
        async for chunk in resp.aiter_text():
            response_buff.append(chunk)

        response_text = ''.join(response_buff)
        if is_notification:
            return None

        content_type = resp.headers.get('Content-Type', '')
        if response_text and content_type.split(';')[0] not in self._response_content_types:
            raise pjrpc.exc.DeserializationError(f"unexpected response content type: {content_type}")

        return response_text

    async def close(self) -> None:
        """
        Closes current http session.
        """

        if self._owned_http_client:
            await self._http_client.aclose()

    async def __aenter__(self) -> 'AsyncClient':
        if self._owned_http_client:
            await self._http_client.__aenter__()

        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._owned_http_client:
            await self._http_client.__aexit__(*args)
