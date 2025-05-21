import abc
import functools as ft
import json
import logging
from typing import Any, Awaitable, Callable, Generator, Generic, Iterable, Mapping, Optional, Protocol

from pjrpc import AbstractRequest, AbstractResponse, BatchRequest, BatchResponse, Request, Response, common
from pjrpc.common import UNSET, MaybeSet, UnsetType, exceptions, generators, v20
from pjrpc.common.typedefs import JsonRpcRequestIdT

logger = logging.getLogger(__package__)


# def validate_response_ids_middleware() -> None:
#     if self.strict and response.id is not None and response.id != request.id:
#             raise exceptions.IdentityError(
#                 f"response id doesn't match the request one: expected {request.id}, got {response.id}",
#             )
#
#         response.related = request


# class BaseBatch(abc.ABC):
#     """
#     Base batch wrapper. Implements some methods to wrap multiple JSON-RPC requests into a single batch request.
#
#     :param client: JSON-RPC client instance
#     """
#
#     class BaseProxy(abc.ABC):
#         """
#         Proxy object. Provides syntactic sugar to make method calls using dot notation.
#
#         :param batch: batch wrapper
#         """
#
#         def __init__(self, batch: 'BaseBatch'):
#             self._batch = batch
#
#         def __getattr__(self, attr: str) -> MethodType:
#             def wrapped(*args: Any, **kwargs: Any) -> 'BaseBatch.BaseProxy':
#                 self._batch.add(attr, *args, **kwargs)
#                 return self
#
#             return wrapped
#
#         @abc.abstractmethod
#         def __call__(self, _trace_ctx: Optional[SimpleNamespace] = None) -> Union[Awaitable[Any], Any]:
#             """
#             Makes an RPC call.
#
#             :param _trace_ctx: tracers request context
#             """
#
#         @abc.abstractmethod
#         def call(self, _trace_ctx: Optional[SimpleNamespace] = None) -> Union[Awaitable[Any], Any]:
#             """
#             Makes an RPC call.
#
#             :param _trace_ctx: tracers request context
#             """
#
#     @property
#     @abc.abstractmethod
#     def proxy(self) -> 'BaseProxy':
#         """
#         Batch request proxy object.
#         """
#
#     def __init__(self, client: 'BaseAbstractClient'):
#         self._client = client
#         self._id_gen = client.id_gen_impl()
#         self._requests = client.batch_request_class()
#
#     def __getitem__(self, requests: Iterable[Tuple[Any]]) -> Union[Awaitable[Any], Any]:
#         """
#         Adds requests to the batch and makes a request.
#
#         :param requests: requests to be added to the batch
#         :returns: request results as a tuple
#         """
#
#         self._requests.extend([
#             self._client.request_class(
#                 method=method,
#                 params=params,
#                 id=next(self._id_gen),
#             ) for method, *params in requests  # type: ignore[var-annotated]
#         ])
#         return self.call()
#
#     def __call__(self, method: str, *args: Any, **kwargs: Any) -> 'BaseBatch':
#         """
#         Adds the method call to the batch.
#
#         :param method: method name
#         :param args: method positional arguments
#         :param kwargs: method named arguments
#         :returns: self
#         """
#
#         return self.add(method, *args, **kwargs)
#
#     @abc.abstractmethod
#     def call(self) -> Union[Awaitable[Any], Any]:
#         """
#         Makes a JSON-RPC request.
#
#         :returns: request results as a tuple
#         """
#
#     @abc.abstractmethod
#     def send(
#         self, request: BatchRequest, **kwargs: Any,
#     ) -> Union[Awaitable[Optional[BatchResponse]], Optional[BatchResponse]]:
#         """
#         Sends a JSON-RPC batch request.
#
#         :param request: request instance
#         :param kwargs: additional client request argument
#         :returns: response instance
#         """
#
#     def add(self, method: str, *args: Any, **kwargs: Any) -> 'BaseBatch':
#         """
#         Adds the method call to the batch.
#
#         :param method: method name
#         :param args: method positional arguments
#         :param kwargs: method named arguments
#         :returns: self
#         """
#
#         assert not (args and kwargs), "positional and keyword arguments are mutually exclusive"
#
#         self._requests.append(self._client.request_class(method, args or kwargs, id=next(self._id_gen)))
#         return self
#
#     def notify(self, method: str, *args: Any, **kwargs: Any) -> 'BaseBatch':
#         """
#         Adds a notification request to the batch.
#
#         :param method: method name
#         :param args: method positional arguments
#         :param kwargs: method named arguments
#         """
#
#         assert not (args and kwargs), "positional and keyword arguments are mutually exclusive"
#
#         self._requests.append(self._client.request_class(method, args or kwargs))
#         return self
#
#     def _relate(self, batch_request: BatchRequest, batch_response: BatchResponse) -> None:
#         """
#         Sets requests `related` field. if `strict` flag is ``True``
#         checks that all requests have theirs corresponding responses
#
#         :param batch_request: batch request
#         :param batch_response: batch response
#         """
#
#         if batch_response.is_success:
#             response_map = {response.id: response for response in batch_response if response.id is not None}
#
#             for request in batch_request:
#                 if request.id is not None:
#                     response = response_map.pop(request.id, None)
#                     if response is None and self._client.strict:
#                         raise exceptions.IdentityError(f"response '{request.id}' not found")
#                     elif response is not None:
#                         response.related = request
#
#             if response_map and self._client.strict:
#                 raise exceptions.IdentityError(f"unexpected response found: {response_map.keys()}")
#
#
# class Batch(BaseBatch):
#     """
#     Batch wrapper. Implements some methods to wrap multiple JSON-RPC requests into a single batch request.
#
#     :param client: JSON-RPC client instance
#     """
#
#     class Proxy(BaseBatch.BaseProxy):
#
#         def __init__(self, batch: 'Batch'):
#             super().__init__(batch)
#
#         def __call__(self) -> Any:
#             return self.call()
#
#         def call(self) -> Any:
#             return self._batch.call()
#
#     @property
#     def proxy(self) -> 'Proxy':
#         return Batch.Proxy(self)
#
#     def __init__(self, client: 'AbstractClient'):
#         super().__init__(client)
#
#     def call(self) -> Optional[Any]:
#         response = self.send(self._requests)
#
#         return response.result if response is not None else None
#
#     def send(self, request: BatchRequest, **kwargs: Any) -> Optional[BatchResponse]:
#         return cast(
#             Optional[BatchResponse], self._client._send(
#                 request,
#                 response_class=self._client.batch_response_class,
#                 validator=self._relate,
#                 **kwargs,
#             ),
#         )
#
#
# class AsyncBatch(BaseBatch):
#     """
#     Asynchronous batch wrapper. Used to make asynchronous JSON-RPC batch requests.
#     """
#
#     class Proxy(BaseBatch.BaseProxy):
#
#         def __init__(self, batch: 'AsyncBatch'):
#             super().__init__(batch)
#
#         async def __call__(self, _trace_ctx: Optional[SimpleNamespace] = None) -> Any:
#             return await self.call(_trace_ctx)
#
#         async def call(self, _trace_ctx: Optional[SimpleNamespace] = None) -> Any:
#             return await self._batch.call(_trace_ctx)
#
#     @property
#     def proxy(self) -> 'Proxy':
#         return AsyncBatch.Proxy(self)
#
#     def __init__(self, client: 'AbstractAsyncClient'):
#         super().__init__(client)
#
#     async def call(self, _trace_ctx: Optional[SimpleNamespace] = None) -> Optional[Any]:
#         response = await self.send(self._requests, _trace_ctx=_trace_ctx)
#
#         return response.result if response is not None else None
#
#     async def send(
#         self, request: BatchRequest, _trace_ctx: Optional[SimpleNamespace] = None, **kwargs: Any,
#     ) -> Optional[BatchResponse]:
#         return await cast(
#             Awaitable[Optional[BatchResponse]], self._client._send(
#                 request,
#                 response_class=self._client.batch_response_class,
#                 validator=self._relate,
#                 _trace_ctx=_trace_ctx,
#                 **kwargs,
#             ),
#         )


MiddlewareHandler = Callable[[AbstractRequest, Mapping[str, Any]], Optional[AbstractResponse]]

class Middleware(Protocol):
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
    """

    class Proxy:
        """
        Proxy object. Provides syntactic sugar to make method call using dot notation.

        :param client: JSON-RPC client instance
        """

        def __init__(self, client: 'AbstractClient'):
            self._client = client

        def __getattr__(self, attr: str) -> Callable[..., Any]:
            return ft.partial(self._client.call, attr)

    @property
    def proxy(self) -> Proxy:
        """
        Clint proxy object.
        """

        return AbstractClient.Proxy(self)

    # @property
    # def batch(self) -> Batch:
    #     """
    #     Client batch wrapper.
    #     """
    #
    #     return Batch(self)

    def __init__(
        self,
        *,
        id_gen_impl: Callable[..., Generator[JsonRpcRequestIdT, None, None]] = generators.sequential,
        request_class: type[v20.Request] = v20.Request,
        response_class: type[v20.Response] = v20.Response,
        batch_request_class: type[v20.BatchRequest] = v20.BatchRequest,
        batch_response_class: type[v20.BatchResponse] = v20.BatchResponse,
        error_cls: type[exceptions.JsonRpcError] = exceptions.JsonRpcError,
        json_loader: Callable[..., Any] = json.loads,
        json_dumper: Callable[..., str] = json.dumps,
        json_encoder: type[common.JSONEncoder] = common.JSONEncoder,
        json_decoder: Optional[json.JSONDecoder] = None,
        middlewares: Iterable[Middleware] = (),
    ):
        self._id_gen_impl = id_gen_impl
        self._request_class = request_class
        self._response_class = response_class
        self._batch_request_class = batch_request_class
        self._batch_response_class = batch_response_class
        self._error_cls = error_cls
        self._json_loader = json_loader
        self._json_dumper = json_dumper
        self._json_encoder = json_encoder
        self._json_decoder = json_decoder

        send = self._send_request
        for middleware in reversed(list(middlewares)):
            send = ft.partial(middleware, handler=send)

        self._send = send

    def __call__(self, method: str, *args: Any, **kwargs: Any) -> Any:
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
        :returns: response instance
        """

        request_text = self._json_dumper(request, cls=self._json_encoder)

        response_text = self._request(request_text, request.is_notification, request_kwargs)
        if not request.is_notification:
            response = self._response_class.from_json(
                self._json_loader(response_text, cls=self._json_decoder), error_cls=self._error_cls,
            )
        else:
            if response_text:
                raise exceptions.BaseError("unexpected response")
            response = None

        return response

    def notify(self, method: str, *args: Any, **kwargs: Any) -> Optional[AbstractResponse]:
        """
        Makes a notification request

        :param method: method name
        :param args: method positional arguments
        :param kwargs: method named arguments
        """

        assert not (args and kwargs), "positional and keyword arguments are mutually exclusive"

        request = self._request_class(
            id=None,
            method=method,
            params=args or kwargs,
        )
        return self._send(request, {})

    def call(self, method: str, *args: Any, **kwargs: Any) -> Any:
        """
        Makes a JSON-RPC call.

        :param method: method name
        :param args: method positional arguments
        :param kwargs: method named arguments
        :returns: response result
        """

        assert not (args and kwargs), "positional and keyword arguments are mutually exclusive"

        request = self._request_class(
            id=next(self._id_gen_impl()),
            method=method,
            params=args or kwargs,
        )
        response = self._send(request, {})

        assert response is not None, "response is not set"
        return response.unwrap_result()


AsyncMiddlewareHandler = Callable[[AbstractRequest, Mapping[str, Any]], Awaitable[Optional[AbstractResponse]]]

class AsyncMiddleware(Protocol):
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
    """

    class Proxy:
        """
        Proxy object. Provides syntactic sugar to make method call using dot notation.

        :param client: JSON-RPC client instance
        """

        def __init__(self, client: 'AbstractAsyncClient'):
            self._client = client

        def __getattr__(self, attr: str) -> Callable[..., Awaitable[Any]]:
            return ft.partial(self._client.call, attr)

    @property
    def proxy(self) -> Proxy:
        """
        Clint proxy object.
        """

        return AbstractAsyncClient.Proxy(self)

    # @property
    # def batch(self) -> AsyncBatch:
    #     """
    #     Client batch wrapper.
    #     """
    #
    #     return AsyncBatch(self)

    def __init__(
        self,
        *,
        id_gen_impl: Callable[..., Generator[JsonRpcRequestIdT, None, None]] = generators.sequential,
        request_class: type[v20.Request] = v20.Request,
        response_class: type[v20.Response] = v20.Response,
        batch_request_class: type[v20.BatchRequest] = v20.BatchRequest,
        batch_response_class: type[v20.BatchResponse] = v20.BatchResponse,
        error_cls: type[exceptions.JsonRpcError] = exceptions.JsonRpcError,
        json_loader: Callable[..., Any] = json.loads,
        json_dumper: Callable[..., str] = json.dumps,
        json_encoder: type[common.JSONEncoder] = common.JSONEncoder,
        json_decoder: Optional[json.JSONDecoder] = None,
        middlewares: Iterable[AsyncMiddleware] = (),
    ):
        self._id_gen_impl = id_gen_impl
        self._request_class = request_class
        self._response_class = response_class
        self._batch_request_class = batch_request_class
        self._batch_response_class = batch_response_class
        self._error_cls = error_cls
        self._json_loader = json_loader
        self._json_dumper = json_dumper
        self._json_encoder = json_encoder
        self._json_decoder = json_decoder

        send = self._send_request
        for middleware in reversed(list(middlewares)):
            send = ft.partial(middleware, handler=send)

        self._send = send

    def __call__(self, method: str, *args: Any, **kwargs: Any) -> Awaitable[Any]:
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

        request_text = self._json_dumper(request, cls=self._json_encoder)

        response_text = await self._request(request_text, request.is_notification, request_kwargs)
        if not request.is_notification:
            response = self._response_class.from_json(
                self._json_loader(response_text, cls=self._json_decoder), error_cls=self._error_cls,
            )
        else:
            if response_text:
                raise exceptions.ProtocolError("unexpected response")
            response = None

        return response

    async def notify(self, method: str, *args: Any, **kwargs: Any) -> Optional[AbstractResponse]:
        """
        Makes a notification request

        :param method: method name
        :param args: method positional arguments
        :param kwargs: method named arguments
        """

        assert not (args and kwargs), "positional and keyword arguments are mutually exclusive"

        request = self._request_class(
            id=None,
            method=method,
            params=args or kwargs,
        )
        return await self._send(request, {})

    async def call(self, method: str, *args: Any, **kwargs: Any) -> Any:
        """
        Makes a JSON-RPC call.

        :param method: method name
        :param args: method positional arguments
        :param kwargs: method named arguments
        :returns: response result
        """

        assert not (args and kwargs), "positional and keyword arguments are mutually exclusive"

        request = self._request_class(
            id=next(self._id_gen_impl()),
            method=method,
            params=args or kwargs,
        )
        response = await self._send(request, {})

        assert response is not None, "response is empty"
        return response.unwrap_result()
