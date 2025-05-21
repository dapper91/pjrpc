import json
import typing
from ssl import SSLContext
from typing import Any, Callable, Generator, Iterable, Mapping, Optional, Self, TypedDict, Union, Unpack

from aiohttp import BasicAuth, Fingerprint, client
from aiohttp.typedefs import LooseCookies, LooseHeaders, StrOrURL
from multidict import MultiDict

import pjrpc
from pjrpc.client import AbstractAsyncClient, AsyncMiddleware
from pjrpc.common import AbstractRequest, AbstractResponse, JSONEncoder, JsonRpcError, generators, v20
from pjrpc.common.typedefs import JsonRpcRequestIdT


class RequestKwArgs(TypedDict):
    cookies: Union[LooseCookies, None]
    headers: Union[LooseHeaders, None]
    skip_auto_headers: Union[Iterable[str], None]
    auth: Union[BasicAuth, None]
    allow_redirects: bool
    max_redirects: int
    compress: Union[str, bool, None]
    chunked: Union[bool, None]
    expect100: bool
    read_until_eof: bool
    proxy: Union[StrOrURL, None]
    proxy_auth: Union[BasicAuth, None]
    timeout: "Union[client.ClientTimeout, None]"
    ssl: Union[SSLContext, bool, Fingerprint]
    server_hostname: Union[str, None]
    proxy_headers: Union[LooseHeaders, None]
    trace_request_ctx: Union[Mapping[str, Any], None]
    read_bufsize: Union[int, None]
    auto_decompress: Union[bool, None]
    max_line_size: Union[int, None]
    max_field_size: Union[int, None]


class Client(AbstractAsyncClient):
    """
    `Aiohttp <https://aiohttp.readthedocs.io/en/stable/client.html>`_ library client backend.

    :param url: url to be used as JSON-RPC endpoint
    :param session: custom session to be used instead of :py:class:`aiohttp.ClientSession`
    :param raise_for_status: should `ClientResponse.raise_for_status()` be called automatically
    :param id_gen_impl: identifier generator
    :param request_class: request class
    :param response_class: response class
    :param batch_request_class: batch request class
    :param batch_response_class: batch response class
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
        session: Optional[client.ClientSession] = None,
        raise_for_status: bool = True,
        id_gen_impl: Callable[..., Generator[JsonRpcRequestIdT, None, None]] = generators.sequential,
        request_class: type[v20.Request] = v20.Request,
        response_class: type[v20.Response] = v20.Response,
        batch_request_class: type[v20.BatchRequest] = v20.BatchRequest,
        batch_response_class: type[v20.BatchResponse] = v20.BatchResponse,
        error_cls: type[JsonRpcError] = JsonRpcError,
        json_loader: Callable[..., Any] = json.loads,
        json_dumper: Callable[..., str] = json.dumps,
        json_encoder: type[JSONEncoder] = JSONEncoder,
        json_decoder: Optional[json.JSONDecoder] = None,
        middlewares: Iterable[AsyncMiddleware] = (),
    ):
        super().__init__(
            id_gen_impl=id_gen_impl,
            request_class=request_class,
            response_class=response_class,
            batch_request_class=batch_request_class,
            batch_response_class=batch_response_class,
            error_cls=error_cls,
            json_loader=json_loader,
            json_dumper=json_dumper,
            json_encoder=json_encoder,
            json_decoder=json_decoder,
            middlewares=middlewares,
        )
        self._endpoint = url
        self._session = session or client.ClientSession()
        self._owned_session = session is None
        self._raise_for_status = raise_for_status

    async def send(self, request: AbstractRequest, **kwargs: Unpack[RequestKwArgs]) -> Optional[AbstractResponse]:
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
        Makes a JSON-RPC request.

        :param request_text: request text representation
        :param is_notification: is the request a notification
        :param request_kwargs: additional client request argument
        :returns: response text representation or None if the request is a notification
        """

        request_kwargs = typing.cast(RequestKwArgs, request_kwargs)

        request_kwargs['headers'] = headers = MultiDict(request_kwargs.get('headers', {}))
        headers['Content-Type'] = pjrpc.common.DEFAULT_CONTENT_TYPE

        async with self._session.post(self._endpoint, data=request_text, **request_kwargs) as resp:
            if self._raise_for_status:
                resp.raise_for_status()
            response_text = await resp.text()

        if is_notification:
            return None

        content_type = resp.headers.get('Content-Type', '')
        if response_text and content_type.split(';')[0] not in pjrpc.common.RESPONSE_CONTENT_TYPES:
            raise pjrpc.exc.DeserializationError(f"unexpected response content type: {content_type}")

        return response_text

    async def close(self) -> None:
        """
        Closes current http session.
        """

        if self._owned_session:
            await self._session.close()

    async def __aenter__(self) -> Self:
        if self._owned_session:
            await self._session.__aenter__()

        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._owned_session:
            await self._session.__aexit__(*args)
