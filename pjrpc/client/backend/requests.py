import json
import typing
from typing import Any, Callable, Generator, Iterable, Mapping, MutableMapping, Optional, Self, TypedDict, Union, Unpack

import requests.auth
import requests.cookies

import pjrpc
from pjrpc.client import AbstractClient, Middleware
from pjrpc.common import AbstractRequest, AbstractResponse, BatchRequest, BatchResponse, JSONEncoder, JsonRpcError
from pjrpc.common import Request, Response, generators
from pjrpc.common.typedefs import JsonRpcRequestIdT


class RequestArgs(TypedDict, total=False):
    headers: Mapping[str, Union[str, bytes, None]]
    cookies: requests.cookies.RequestsCookieJar
    auth: Union[tuple[str, str], requests.auth.AuthBase]
    timeout: Union[float, tuple[float, float], tuple[float, None]]
    allow_redirects: bool
    proxies: MutableMapping[str, str]
    hooks: Mapping[str, Union[Iterable[Callable[[requests.Response], Any]], Callable[[requests.Response], Any]]]
    verify: Union[bool, str]
    cert: Union[str, tuple[str, str]]


class Client(AbstractClient):
    """
    `Requests <https://2.python-requests.org/>`_ library client backend.

    :param url: url to be used as JSON-RPC endpoint.
    :param session: custom session to be used instead of :py:class:`requests.Session`
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
        session: Optional[requests.Session] = None,
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
        self._session = session or requests.Session()
        self._owned_session = session is None
        self._raise_for_status = raise_for_status

    @typing.overload
    def send(self, request: Request, **kwargs: Unpack[RequestArgs]) -> Optional[Response]:
        ...

    @typing.overload
    def send(self, request: BatchRequest, **kwargs: Unpack[RequestArgs]) -> Optional[BatchResponse]:
        ...

    def send(self, request: AbstractRequest, **kwargs: Unpack[RequestArgs]) -> Optional[AbstractResponse]:
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
        :returns: response text
        """

        request_kwargs = typing.cast(RequestArgs, request_kwargs)

        request_kwargs['headers'] = headers = dict(request_kwargs.get('headers', {}))
        headers['Content-Type'] = self._request_content_type

        resp = self._session.post(self._endpoint, data=request_text, **request_kwargs)
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

        if self._owned_session:
            self._session.close()

    def __enter__(self) -> Self:
        if self._owned_session:
            self._session.__enter__()

        return self

    def __exit__(self, *args: Any) -> None:
        if self._owned_session:
            self._session.__exit__(*args)
