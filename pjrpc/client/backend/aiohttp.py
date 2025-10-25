import json
import typing
from ssl import SSLContext
from typing import Any, Callable, Generator, Iterable, Mapping, Optional, Self, TypedDict, Union, Unpack

from aiohttp import BasicAuth, Fingerprint, client
from aiohttp.typedefs import LooseCookies, LooseHeaders, StrOrURL
from multidict import MultiDict

import pjrpc
from pjrpc.client import AbstractAsyncClient, AsyncMiddleware
from pjrpc.common import AbstractRequest, AbstractResponse, BatchRequest, BatchResponse, JSONEncoder, JsonRpcError
from pjrpc.common import Request, Response, generators
from pjrpc.common.typedefs import JsonRpcRequestIdT


class RequestArgs(TypedDict, total=False):
    cookies: LooseCookies
    headers: LooseHeaders
    skip_auto_headers: Iterable[str]
    auth: BasicAuth
    allow_redirects: bool
    max_redirects: int
    compress: Union[str, bool]
    chunked: bool
    expect100: bool
    read_until_eof: bool
    proxy: StrOrURL
    proxy_auth: BasicAuth
    timeout: "Union[client.ClientTimeout, None]"
    ssl: Union[SSLContext, bool, Fingerprint]
    server_hostname: str
    proxy_headers: LooseHeaders
    trace_request_ctx: Mapping[str, Any]
    read_bufsize: int
    auto_decompress: bool
    max_line_size: int
    max_field_size: int


class Client(AbstractAsyncClient):
    """
    `Aiohttp <https://aiohttp.readthedocs.io/en/stable/client.html>`_ library client backend.

    :param url: url to be used as JSON-RPC endpoint
    :param session: custom session to be used instead of :py:class:`aiohttp.ClientSession`
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
        session: Optional[client.ClientSession] = None,
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
        self._session = session or client.ClientSession()
        self._owned_session = session is None
        self._raise_for_status = raise_for_status

    @typing.overload
    async def send(self, request: Request, **kwargs: Unpack[RequestArgs]) -> Optional[Response]:
        ...

    @typing.overload
    async def send(self, request: BatchRequest, **kwargs: Unpack[RequestArgs]) -> Optional[BatchResponse]:
        ...

    async def send(self, request: AbstractRequest, **kwargs: Unpack[RequestArgs]) -> Optional[AbstractResponse]:
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

        request_kwargs = typing.cast(RequestArgs, request_kwargs)

        request_kwargs['headers'] = headers = MultiDict(request_kwargs.get('headers', {}))
        headers['Content-Type'] = self._request_content_type

        async with self._session.post(self._endpoint, data=request_text, **request_kwargs) as resp:
            if self._raise_for_status:
                resp.raise_for_status()
            response_text = await resp.text()

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

        if self._owned_session:
            await self._session.close()

    async def __aenter__(self) -> Self:
        if self._owned_session:
            await self._session.__aenter__()

        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._owned_session:
            await self._session.__aexit__(*args)
