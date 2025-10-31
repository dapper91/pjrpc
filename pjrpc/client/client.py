import abc
import contextlib as cl
import functools as ft
import json
import logging
from typing import Any, AsyncGenerator, Awaitable, Callable, Generator, Iterable, Mapping, Optional, Protocol, TypeVar

from pjrpc import common
from pjrpc.common import UNSET, AbstractRequest, AbstractResponse, BatchRequest, BatchResponse, MaybeSet, Request
from pjrpc.common import Response, generators
from pjrpc.common.typedefs import JsonRpcRequestIdT, JsonT

from . import exceptions

logger = logging.getLogger(__package__)


ReturnT = TypeVar('ReturnT', covariant=True)


class ProxyCall(Protocol[ReturnT]):
    def __call__(self, *args: JsonT, **kwargs: JsonT) -> ReturnT: pass


class Batch:
    """
    Batch object. Provides syntactic sugar to send batch requests.
    """

    class Proxy:
        """
        Proxy object. Provides syntactic sugar to make method call using dot notation.

        :param batch: batch object
        """

        def __init__(self, batch: 'Batch'):
            self._batch = batch

        def __getattr__(self, attr: str) -> ProxyCall[JsonT]:
            return ft.partial(self._batch.call, attr)

    def __init__(
        self,
        id_gen_impl: Callable[..., Generator[JsonRpcRequestIdT, None, None]],
    ):
        self._id_gen = id_gen_impl()

        self._requests: list[Request] = []
        self._response: MaybeSet[Optional[BatchResponse]] = UNSET

    @property
    def proxy(self) -> Proxy:
        """
        Client proxy object.
        """

        return Batch.Proxy(self)

    @property
    def requests(self) -> list[Request]:
        """
        Batch requests.
        """

        return self._requests

    def __call__(self, method: str, *args: JsonT, **kwargs: JsonT) -> None:
        """
        Makes a JSON-RPC call.

        :param method: method name
        :param args: method positional arguments
        :param kwargs: method named arguments
        :returns: response result
        """

        assert not (args and kwargs), "positional and keyword arguments are mutually exclusive"

        self._requests.append(Request(id=next(self._id_gen), method=method, params=args or kwargs))

    def send(self, request: Request) -> None:
        self._requests.append(request)

    def notify(self, method: str, *args: JsonT, **kwargs: JsonT) -> None:
        """
        Makes a notification request

        :param method: method name
        :param args: method positional arguments
        :param kwargs: method named arguments
        """

        assert not (args and kwargs), "positional and keyword arguments are mutually exclusive"

        self._requests.append(Request(id=None, method=method, params=args or kwargs))

    def call(self, method: str, *args: JsonT, **kwargs: JsonT) -> None:
        """
        Makes a JSON-RPC call.

        :param method: method name
        :param args: method positional arguments
        :param kwargs: method named arguments
        :returns: response result
        """

        assert not (args and kwargs), "positional and keyword arguments are mutually exclusive"

        self._requests.append(Request(id=next(self._id_gen), method=method, params=args or kwargs))

    def set_response(self, response: Optional[BatchResponse]) -> None:
        """
        Sets batch response
        """

        self._response = response

    def get_response(self) -> Optional[BatchResponse]:
        """
        Returns a batch response.
        """

        if self._response is UNSET:
            raise RuntimeError("batch reqeust is not sent yet")

        return self._response

    def get_results(self) -> Iterable[Any]:
        """
        Returns the batch results preserving requests order (skipping notification request).
        """

        if self._response is UNSET:
            raise RuntimeError("batch reqeust is not sent yet")
        if self._response is None:
            return []

        if self._response.is_error:
            raise self._response.unwrap_error()

        response_map = {response.id: response for response in self._response}
        results: list[Any] = []
        for request in self._requests:
            if request.id is not None:
                if (response := response_map.get(request.id)) is None:
                    raise exceptions.IdentityError(f"response '{request.id}' is missing")
                results.append(response.unwrap_result())

        return results


MiddlewareHandler = Callable[[AbstractRequest, Mapping[str, Any]], Optional[AbstractResponse]]


class Middleware(Protocol):
    """
    JSON-RPC client middleware.
    """

    def __call__(
        self,
        request: AbstractRequest,
        request_kwargs: Mapping[str, Any],
        /,
        handler: MiddlewareHandler,
    ) -> Optional[AbstractResponse]:
        pass


class AbstractClient(abc.ABC):
    """
    Abstract synchronous JSON-RPC client.

    :param id_gen_impl: identifier generator
    :param error_cls: JSON-RPC error base class
    :param json_loader: json loader
    :param json_dumper: json dumper
    :param json_encoder: json encoder
    :param json_decoder: json decoder
    :param middlewares: client reqeust middlewares
    """

    class Proxy:
        """
        Proxy object. Provides syntactic sugar to make method call using dot notation.

        :param client: JSON-RPC client instance
        """

        def __init__(self, client: 'AbstractClient'):
            self._client = client

        def __getattr__(self, attr: str) -> ProxyCall[JsonT]:
            return ft.partial(self._client.call, attr)

    @property
    def proxy(self) -> Proxy:
        """
        Client proxy object.
        """

        return AbstractClient.Proxy(self)

    @cl.contextmanager
    def batch(self) -> Generator[Batch, None, None]:
        """
        Client batch wrapper.
        """

        batch = Batch(self._id_gen_impl)
        yield batch

        response = self._send(BatchRequest(*batch.requests), {})
        assert isinstance(response, (BatchResponse, type(None))), "unexpected response type"

        batch.set_response(response)

    def __init__(
        self,
        *,
        id_gen_impl: Callable[..., Generator[JsonRpcRequestIdT, None, None]] = generators.sequential,
        error_cls: type[exceptions.JsonRpcError] = exceptions.JsonRpcError,
        json_loader: Callable[..., Any] = json.loads,
        json_dumper: Callable[..., str] = json.dumps,
        json_encoder: type[common.JSONEncoder] = common.JSONEncoder,
        json_decoder: Optional[json.JSONDecoder] = None,
        middlewares: Iterable[Middleware] = (),
        request_content_type: str = common.DEFAULT_CONTENT_TYPE,
        response_content_types: Iterable[str] = common.RESPONSE_CONTENT_TYPES,
    ):
        self._id_gen_impl = id_gen_impl
        self._error_cls = error_cls
        self._json_loader = json_loader
        self._json_dumper = json_dumper
        self._json_encoder = json_encoder
        self._json_decoder = json_decoder
        self._request_content_type = request_content_type
        self._response_content_types = set(response_content_types)

        send = self._send_request
        for middleware in reversed(list(middlewares)):
            send = ft.partial(middleware, handler=send)

        self._send = send

    def __call__(self, method: str, *args: JsonT, **kwargs: JsonT) -> JsonT:
        """
        Makes a JSON-RPC call.

        :param method: method name
        :param args: method positional arguments
        :param kwargs: method named arguments
        :returns: response result
        """

        return self.call(method, *args, **kwargs)

    @abc.abstractmethod
    def _request(
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
        :returns: response text representation
        """

    def _send_request(
        self,
        request: AbstractRequest,
        request_kwargs: Mapping[str, Any],
    ) -> Optional[AbstractResponse]:
        """
        Sends a JSON-RPC request.

        :param request: request instance
        :param request_kwargs: additional client request argument
        :returns: response instance or None if the request is a notification
        """

        response_cls: type[AbstractResponse] = BatchResponse if isinstance(request, BatchRequest) else Response
        request_text = self._json_dumper(request, cls=self._json_encoder)

        response_text = self._request(request_text, request.is_notification, request_kwargs)
        if not request.is_notification:
            response = response_cls.from_json(
                self._json_loader(response_text, cls=self._json_decoder), error_cls=self._error_cls,
            )
        else:
            if response_text:
                raise exceptions.ProtocolError("unexpected response")
            response = None

        return response

    def notify(self, method: str, *args: JsonT, **kwargs: JsonT) -> None:
        """
        Makes a notification request

        :param method: method name
        :param args: method positional arguments
        :param kwargs: method named arguments
        """

        assert not (args and kwargs), "positional and keyword arguments are mutually exclusive"

        request = Request(
            id=None,
            method=method,
            params=args or kwargs,
        )
        self._send(request, {})

    def call(self, method: str, *args: JsonT, **kwargs: JsonT) -> JsonT:
        """
        Makes a JSON-RPC call.

        :param method: method name
        :param args: method positional arguments
        :param kwargs: method named arguments
        :returns: response result
        """

        assert not (args and kwargs), "positional and keyword arguments are mutually exclusive"

        request = Request(
            id=next(self._id_gen_impl()),
            method=method,
            params=args or kwargs,
        )
        response = self._send(request, {})

        assert response is not None, "response is not set"
        return response.unwrap_result()


AsyncMiddlewareHandler = Callable[[AbstractRequest, Mapping[str, Any]], Awaitable[Optional[AbstractResponse]]]


class AsyncMiddleware(Protocol):
    """
    Asynchronous JSON-RPC client middleware.
    """

    async def __call__(
        self,
        request: AbstractRequest,
        request_kwargs: Mapping[str, Any],
        /,
        handler: AsyncMiddlewareHandler,
    ) -> Optional[AbstractResponse]:
        pass


class AbstractAsyncClient(abc.ABC):
    """
    Abstract asynchronous JSON-RPC client.

    :param id_gen_impl: identifier generator
    :param error_cls: JSON-RPC error base class
    :param json_loader: json loader
    :param json_dumper: json dumper
    :param json_encoder: json encoder
    :param json_decoder: json decoder
    :param middlewares: client reqeust middlewares
    """

    class Proxy:
        """
        Proxy object. Provides syntactic sugar to make method call using dot notation.

        :param client: JSON-RPC client instance
        """

        def __init__(self, client: 'AbstractAsyncClient'):
            self._client = client

        def __getattr__(self, attr: str) -> Callable[..., Awaitable[JsonT]]:
            return ft.partial(self._client.call, attr)

    @property
    def proxy(self) -> Proxy:
        """
        Client proxy object.
        """

        return AbstractAsyncClient.Proxy(self)

    @cl.asynccontextmanager
    async def batch(self) -> AsyncGenerator[Batch, None]:
        """
        Client batch wrapper.
        """

        batch = Batch(self._id_gen_impl)
        yield batch

        response = await self._send(BatchRequest(*batch.requests), {})
        assert isinstance(response, (BatchResponse, type(None))), "unexpected response type"

        batch.set_response(response)

    def __init__(
        self,
        *,
        id_gen_impl: Callable[..., Generator[JsonRpcRequestIdT, None, None]] = generators.sequential,
        error_cls: type[exceptions.JsonRpcError] = exceptions.JsonRpcError,
        json_loader: Callable[..., Any] = json.loads,
        json_dumper: Callable[..., str] = json.dumps,
        json_encoder: type[common.JSONEncoder] = common.JSONEncoder,
        json_decoder: Optional[json.JSONDecoder] = None,
        middlewares: Iterable[AsyncMiddleware] = (),
        request_content_type: str = common.DEFAULT_CONTENT_TYPE,
        response_content_types: Iterable[str] = common.RESPONSE_CONTENT_TYPES,
    ):
        self._id_gen_impl = id_gen_impl
        self._error_cls = error_cls
        self._json_loader = json_loader
        self._json_dumper = json_dumper
        self._json_encoder = json_encoder
        self._json_decoder = json_decoder
        self._request_content_type = request_content_type
        self._response_content_types = set(response_content_types)

        send = self._send_request
        for middleware in reversed(list(middlewares)):
            send = ft.partial(middleware, handler=send)

        self._send = send

    def __call__(self, method: str, *args: JsonT, **kwargs: JsonT) -> Awaitable[JsonT]:
        """
        Makes a JSON-RPC call.

        :param method: method name
        :param args: method positional arguments
        :param kwargs: method named arguments
        :returns: response result
        """

        return self.call(method, *args, **kwargs)

    @abc.abstractmethod
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

    async def _send_request(
        self,
        request: AbstractRequest,
        request_kwargs: Mapping[str, Any],
    ) -> Optional[AbstractResponse]:
        """
        Sends a JSON-RPC request.

        :param request: request instance
        :param request_kwargs: additional client request argument
        :returns: response instance or None if the request is a notification
        """

        response_cls: type[AbstractResponse] = BatchResponse if isinstance(request, BatchRequest) else Response
        request_text = self._json_dumper(request, cls=self._json_encoder)

        response_text = await self._request(request_text, request.is_notification, request_kwargs)
        if not request.is_notification:
            response = response_cls.from_json(
                self._json_loader(response_text, cls=self._json_decoder), error_cls=self._error_cls,
            )
        else:
            if response_text:
                raise exceptions.ProtocolError("unexpected response")
            response = None

        return response

    async def notify(self, method: str, *args: JsonT, **kwargs: JsonT) -> None:
        """
        Makes a notification request

        :param method: method name
        :param args: method positional arguments
        :param kwargs: method named arguments
        """

        assert not (args and kwargs), "positional and keyword arguments are mutually exclusive"

        request = Request(
            id=None,
            method=method,
            params=args or kwargs,
        )
        await self._send(request, {})

    async def call(self, method: str, *args: JsonT, **kwargs: JsonT) -> JsonT:
        """
        Makes a JSON-RPC call.

        :param method: method name
        :param args: method positional arguments
        :param kwargs: method named arguments
        :returns: response result
        """

        assert not (args and kwargs), "positional and keyword arguments are mutually exclusive"

        request = Request(
            id=next(self._id_gen_impl()),
            method=method,
            params=args or kwargs,
        )
        response = await self._send(request, {})

        assert response is not None, "response is empty"
        return response.unwrap_result()
