import abc
import functools as ft
import json
import logging
from types import SimpleNamespace
from typing import Any, Awaitable, Callable, Dict, Generator, Iterable, Optional, Tuple, Type, Union, cast

from pjrpc import AbstractRequest, AbstractResponse, BatchRequest, BatchResponse, Request, Response, common
from pjrpc.client import retry
from pjrpc.common import UNSET, UnsetType, exceptions, generators, v20
from pjrpc.common.typedefs import JsonRpcRequestId, MethodType

from .tracer import Tracer

logger = logging.getLogger(__package__)


class BaseBatch(abc.ABC):
    """
    Base batch wrapper. Implements some methods to wrap multiple JSON-RPC requests into a single batch request.

    :param client: JSON-RPC client instance
    """

    class BaseProxy(abc.ABC):
        """
        Proxy object. Provides syntactic sugar to make method calls using dot notation.

        :param batch: batch wrapper
        """

        def __init__(self, batch: 'BaseBatch'):
            self._batch = batch

        def __getattr__(self, attr: str) -> MethodType:
            def wrapped(*args: Any, **kwargs: Any) -> 'BaseBatch.BaseProxy':
                self._batch.add(attr, *args, **kwargs)
                return self

            return wrapped

        @abc.abstractmethod
        def __call__(self, _trace_ctx: SimpleNamespace = SimpleNamespace()) -> Union[Awaitable[Any], Any]:
            """
            Makes an RPC call.

            :param _trace_ctx: tracers request context
            """

        @abc.abstractmethod
        def call(self, _trace_ctx: SimpleNamespace = SimpleNamespace()) -> Union[Awaitable[Any], Any]:
            """
            Makes an RPC call.

            :param _trace_ctx: tracers request context
            """

    @property
    @abc.abstractmethod
    def proxy(self) -> 'BaseProxy':
        """
        Batch request proxy object.
        """

    def __init__(self, client: 'BaseAbstractClient'):
        self._client = client
        self._id_gen = client.id_gen_impl()
        self._requests = client.batch_request_class()

    def __getitem__(self, requests: Iterable[Tuple]) -> Union[Awaitable[Any], Any]:
        """
        Adds requests to the batch and makes a request.

        :param requests: requests to be added to the batch
        :returns: request results as a tuple
        """

        self._requests.extend([
            self._client.request_class(
                method=method,
                params=params,
                id=next(self._id_gen),
            ) for method, *params in requests
        ])
        return self.call()

    def __call__(self, method: str, *args: Any, **kwargs: Any) -> 'BaseBatch':
        """
        Adds the method call to the batch.

        :param method: method name
        :param args: method positional arguments
        :param kwargs: method named arguments
        :returns: self
        """

        return self.add(method, *args, **kwargs)

    @abc.abstractmethod
    def call(self, _trace_ctx: SimpleNamespace = SimpleNamespace()) -> Union[Awaitable[Any], Any]:
        """
        Makes a JSON-RPC request.

        :param _trace_ctx: tracers request context
        :returns: request results as a tuple
        """

    @abc.abstractmethod
    def send(
        self, request: BatchRequest, _trace_ctx: SimpleNamespace = SimpleNamespace(), **kwargs: Any,
    ) -> Union[Awaitable[Optional[BatchResponse]], Optional[BatchResponse]]:
        """
        Sends a JSON-RPC batch request.

        :param request: request instance
        :param kwargs: additional client request argument
        :param _trace_ctx: tracers request context
        :returns: response instance
        """

    def add(self, method: str, *args: Any, **kwargs: Any) -> 'BaseBatch':
        """
        Adds the method call to the batch.

        :param method: method name
        :param args: method positional arguments
        :param kwargs: method named arguments
        :returns: self
        """

        assert not (args and kwargs), "positional and keyword arguments are mutually exclusive"

        self._requests.append(self._client.request_class(method, args or kwargs, id=next(self._id_gen)))
        return self

    def notify(self, method: str, *args: Any, **kwargs: Any) -> 'BaseBatch':
        """
        Adds a notification request to the batch.

        :param method: method name
        :param args: method positional arguments
        :param kwargs: method named arguments
        """

        assert not (args and kwargs), "positional and keyword arguments are mutually exclusive"

        self._requests.append(self._client.request_class(method, args or kwargs))
        return self

    def _relate(self, batch_request: BatchRequest, batch_response: BatchResponse) -> None:
        """
        Sets requests `related` field. if `strict` flag is ``True``
        checks that all requests have theirs corresponding responses

        :param batch_request: batch request
        :param batch_response: batch response
        """

        if batch_response.is_success:
            response_map = {response.id: response for response in batch_response if response.id is not None}

            for request in batch_request:
                if request.id is not None:
                    response = response_map.pop(request.id, None)
                    if response is None and self._client.strict:
                        raise exceptions.IdentityError(f"response '{request.id}' not found")
                    elif response is not None:
                        response.related = request

            if response_map and self._client.strict:
                raise exceptions.IdentityError(f"unexpected response found: {response_map.keys()}")


class Batch(BaseBatch):
    """
    Batch wrapper. Implements some methods to wrap multiple JSON-RPC requests into a single batch request.

    :param client: JSON-RPC client instance
    """

    class Proxy(BaseBatch.BaseProxy):

        def __init__(self, batch: 'Batch'):
            super().__init__(batch)

        def __call__(self, _trace_ctx: SimpleNamespace = SimpleNamespace()) -> Any:
            return self.call(_trace_ctx)

        def call(self, _trace_ctx: SimpleNamespace = SimpleNamespace()) -> Any:
            return self._batch.call(_trace_ctx)

    @property
    def proxy(self) -> 'Proxy':
        return Batch.Proxy(self)

    def __init__(self, client: 'AbstractClient'):
        super().__init__(client)

    def call(self, _trace_ctx: SimpleNamespace = SimpleNamespace()) -> Optional[Any]:
        response = self.send(self._requests)

        return response.result if response is not None else None

    def send(
        self, request: BatchRequest, _trace_ctx: SimpleNamespace = SimpleNamespace(), **kwargs: Any,
    ) -> Optional[BatchResponse]:
        return cast(
            Optional[BatchResponse], self._client._send(
                request,
                response_class=self._client.batch_response_class,
                validator=self._relate,
                _trace_ctx=_trace_ctx,
                **kwargs,
            ),
        )


class AsyncBatch(BaseBatch):
    """
    Asynchronous batch wrapper. Used to make asynchronous JSON-RPC batch requests.
    """

    class Proxy(BaseBatch.BaseProxy):

        def __init__(self, batch: 'AsyncBatch'):
            super().__init__(batch)

        async def __call__(self, _trace_ctx: SimpleNamespace = SimpleNamespace()) -> Any:
            return await self.call(_trace_ctx)

        async def call(self, _trace_ctx: SimpleNamespace = SimpleNamespace()) -> Any:
            return await self._batch.call(_trace_ctx)

    @property
    def proxy(self) -> 'Proxy':
        return AsyncBatch.Proxy(self)

    def __init__(self, client: 'AbstractAsyncClient'):
        super().__init__(client)

    async def call(self, _trace_ctx: SimpleNamespace = SimpleNamespace()) -> Optional[Any]:
        response = await self.send(self._requests, _trace_ctx=_trace_ctx)

        return response.result if response is not None else None

    async def send(
        self, request: BatchRequest, _trace_ctx: SimpleNamespace = SimpleNamespace(), **kwargs: Any,
    ) -> Optional[BatchResponse]:
        return await cast(
            Awaitable[Optional[BatchResponse]], self._client._send(
                request,
                response_class=self._client.batch_response_class,
                validator=self._relate,
                _trace_ctx=_trace_ctx,
                **kwargs,
            ),
        )


class BaseAbstractClient(abc.ABC):
    """
    Base abstract JSON-RPC client.

    :param request_class: request class
    :param response_class: response class
    :param batch_request_class: batch request class
    :param batch_response_class: batch response class
    :param error_cls: JSON-RPC error base class
    :param id_gen_impl: identifier generator
    :param json_loader: json loader
    :param json_dumper: json dumper
    :param json_encoder: json encoder
    :param json_decoder: json decoder
    :param strict: if ``True`` checks that a request and a response identifiers match
    :param request_args: backend request argument
    :param tracers: request tracers list
    :param retry_strategy: request retry strategy
    """

    class Proxy:
        """
        Proxy object. Provides syntactic sugar to make method call using dot notation.

        :param client: JSON-RPC client instance
        """

        def __init__(self, client: 'BaseAbstractClient'):
            self._client = client

        def __getattr__(self, attr: str) -> Callable:
            return ft.partial(self._client.call, attr)

    def __init__(
        self,
        request_class: Type[Request] = v20.Request,
        response_class: Type[Response] = v20.Response,
        batch_request_class: Type[BatchRequest] = v20.BatchRequest,
        batch_response_class: Type[BatchResponse] = v20.BatchResponse,
        error_cls: Type[exceptions.JsonRpcError] = exceptions.JsonRpcError,
        id_gen_impl: Callable[..., Generator[JsonRpcRequestId, None, None]] = generators.sequential,
        json_loader: Callable = json.loads,
        json_dumper: Callable = json.dumps,
        json_encoder: Type[common.JSONEncoder] = common.JSONEncoder,
        json_decoder: Optional[json.JSONDecoder] = None,
        strict: bool = True,
        request_args: Optional[Dict[str, Any]] = None,
        tracers: Iterable[Tracer] = (),
        retry_strategy: Optional[retry.RetryStrategy] = None,
    ):
        self.request_class = request_class
        self.response_class = response_class
        self.batch_request_class = batch_request_class
        self.batch_response_class = batch_response_class
        self.error_cls = error_cls
        self.json_loader = json_loader
        self.json_dumper = json_dumper
        self.json_encoder = json_encoder
        self.json_decoder = json_decoder
        self.id_gen_impl = id_gen_impl
        self.strict = strict
        self._request_args = request_args or {}
        self._tracers = tracers
        self._retry_strategy = retry_strategy

    def __call__(
        self,
        method: str,
        *args: Any,
        _trace_ctx: SimpleNamespace = SimpleNamespace(),
        **kwargs: Any,
    ) -> Union[Awaitable[Any], Any]:
        """
        Makes JSON-RPC call.

        :param method: method name
        :param args: method positional arguments
        :param kwargs: method named arguments
        :param _trace_ctx: tracers request context
        :returns: response result
        """

        return self.call(method, *args, **kwargs)

    @property
    def proxy(self) -> 'Proxy':
        """
        Clint proxy object.
        """

        return BaseAbstractClient.Proxy(self)

    @abc.abstractmethod
    def call(self, method: str, *args: Any, **kwargs: Any) -> Union[Awaitable[Any], Any]:
        pass

    @abc.abstractmethod
    def _send(
        self,
        request: AbstractRequest,
        response_class: Type[AbstractResponse],
        validator: Callable[..., None],
        _trace_ctx: SimpleNamespace = SimpleNamespace(),
        **kwargs: Any,
    ) -> Union[Awaitable[Optional[AbstractResponse]], Optional[AbstractResponse]]:
        pass

    def _relate(self, request: Request, response: Response) -> None:
        """
        Checks the the request and the response identifiers match.

        :param request: request
        :param response: response
        """

        if self.strict and response.id is not None and response.id != request.id:
            raise exceptions.IdentityError(
                f"response id doesn't match the request one: expected {request.id}, got {response.id}",
            )

        response.related = request


class AbstractClient(BaseAbstractClient):
    """
    Abstract synchronous JSON-RPC client.
    """

    @property
    def batch(self) -> Batch:
        """
        Client batch wrapper.
        """

        return Batch(self)

    @abc.abstractmethod
    def _request(self, request_text: str, is_notification: bool = False, **kwargs: Any) -> Optional[str]:
        """
        Makes a JSON-RPC request.

        :param request_text: request text representation
        :param is_notification: is the request a notification
        :returns: response text representation
        """

    def notify(
        self,
        method: str,
        *args: Any,
        _trace_ctx: SimpleNamespace = SimpleNamespace(),
        **kwargs: Any,
    ) -> Optional[Response]:
        """
        Makes a notification request

        :param method: method name
        :param args: method positional arguments
        :param kwargs: method named arguments
        :param _trace_ctx: tracers request context
        """

        assert not (args and kwargs), "positional and keyword arguments are mutually exclusive"

        request = self.request_class(
            id=None,
            method=method,
            params=args or kwargs,
        )
        return self.send(request, _trace_ctx=_trace_ctx)

    def call(
        self, method: str, *args: Any, _trace_ctx: SimpleNamespace = SimpleNamespace(), **kwargs: Any,
    ) -> Any:
        """
        Makes JSON-RPC call.

        :param method: method name
        :param args: method positional arguments
        :param kwargs: method named arguments
        :param _trace_ctx: tracers request context
        :returns: response result
        """

        assert not (args and kwargs), "positional and keyword arguments are mutually exclusive"

        request = self.request_class(
            id=next(self.id_gen_impl()),
            method=method,
            params=args or kwargs,
        )
        response = self.send(request, _trace_ctx=_trace_ctx)

        assert response is not None, "response is not set"
        return response.result

    def send(
        self,
        request: Request,
        _trace_ctx: SimpleNamespace = SimpleNamespace(),
        _retry_strategy: Union[UnsetType, retry.RetryStrategy] = UNSET,
        **kwargs: Any,
    ) -> Optional[Response]:
        """
        Sends a JSON-RPC request.

        :param request: request instance
        :param kwargs: additional client request argument
        :param _trace_ctx: tracers request context
        :param _retry_strategy: request retry strategy
        :returns: response instance
        """

        return cast(
            Response, self._send(
                request,
                response_class=self.response_class,
                validator=self._relate,
                _trace_ctx=_trace_ctx,
                _retry_strategy=_retry_strategy,
                **kwargs,
            ),
        )

    def traced(method: Callable[..., Any]) -> Callable[..., Any]:
        @ft.wraps(method)
        def wrapper(
            self: 'AbstractClient',
            request: AbstractRequest,
            _trace_ctx: SimpleNamespace,
            **kwargs: Any,
        ) -> Optional[AbstractResponse]:
            """
            Adds tracing logic to the method.
            """

            for tracer in self._tracers:
                tracer.on_request_begin(_trace_ctx, request)

            try:
                response = method(self, request, _trace_ctx=_trace_ctx, **kwargs)
            except BaseException as e:
                for tracer in self._tracers:
                    tracer.on_error(_trace_ctx, request, e)
                raise

            for tracer in self._tracers:
                tracer.on_request_end(_trace_ctx, request, response)

            return response

        return wrapper

    def retried(method: Callable[..., Any]) -> Callable[..., Any]:
        @ft.wraps(method)
        def wrapper(
            self: 'AbstractClient',
            request: AbstractRequest,
            _retry_strategy: Union[UnsetType, retry.RetryStrategy] = UNSET,
            **kwargs: Any,
        ) -> Optional[AbstractResponse]:
            """
            Adds retrying logic to the method.
            """

            retry_strategy = self._retry_strategy if isinstance(_retry_strategy, UnsetType) else _retry_strategy
            if retry_strategy:
                wrapped_method = retry.retry(method, retry_strategy)
            else:
                wrapped_method = method

            response = wrapped_method(self, request, **kwargs)

            return response

        return wrapper

    @retried
    @traced
    def _send(
        self,
        request: AbstractRequest,
        response_class: Type[AbstractResponse],
        validator: Callable[..., None],
        _trace_ctx: SimpleNamespace = SimpleNamespace(),
        **kwargs: Any,
    ) -> Optional[AbstractResponse]:
        kwargs = {**self._request_args, **kwargs}
        request_text = self.json_dumper(request, cls=self.json_encoder)

        response_text = self._request(request_text, request.is_notification, **kwargs)
        if not request.is_notification:
            response = response_class.from_json(
                self.json_loader(response_text, cls=self.json_decoder), error_cls=self.error_cls,
            )
            validator(request, response)

        else:
            if self.strict and response_text:
                raise exceptions.BaseError("unexpected response")
            response = None

        return response


class AbstractAsyncClient(BaseAbstractClient):
    """
    Abstract asynchronous JSON-RPC client.
    """

    @property
    def batch(self) -> AsyncBatch:
        """
        Client batch wrapper.
        """

        return AsyncBatch(self)

    @abc.abstractmethod
    async def _request(self, request_text: str, is_notification: bool = False, **kwargs: Any) -> Optional[str]:
        """
        Makes a JSON-RPC request.

        :param request_text: request text representation
        :param is_notification: is the request a notification
        :returns: response text representation
        """

    async def send(
        self,
        request: Request,
        _trace_ctx: SimpleNamespace = SimpleNamespace(),
        _retry_strategy: Union[UnsetType, retry.RetryStrategy] = UNSET,
        **kwargs: Any,
    ) -> Optional[Response]:
        """
        Sends a JSON-RPC request.

        :param request: request instance
        :param kwargs: additional client request argument
        :param _trace_ctx: tracers request context
        :param _retry_strategy: request retry strategy
        :returns: response instance
        """

        return cast(
            Response, await self._send(
                request,
                _trace_ctx=_trace_ctx,
                _retry_strategy=_retry_strategy,
                response_class=self.response_class,
                validator=self._relate,
                **kwargs,
            ),
        )

    def traced(method: Callable[..., Any]) -> Callable[..., Any]:
        @ft.wraps(method)
        async def wrapper(
            self: 'AbstractAsyncClient',
            request: Request,
            _trace_ctx: SimpleNamespace = SimpleNamespace(),
            **kwargs: Any,
        ) -> Response:
            """
            Adds tracing logic to the method.
            """

            for tracer in self._tracers:
                tracer.on_request_begin(_trace_ctx, request)

            try:
                response = await method(self, request, _trace_ctx=_trace_ctx, **kwargs)
            except BaseException as e:
                for tracer in self._tracers:
                    tracer.on_error(_trace_ctx, request, e)
                raise

            for tracer in self._tracers:
                tracer.on_request_end(_trace_ctx, request, response)

            return response

        return wrapper

    def retried(method: Callable[..., Awaitable[Any]]) -> Callable[..., Any]:
        @ft.wraps(method)
        async def wrapper(
            self: 'AbstractClient',
            request: AbstractRequest,
            _retry_strategy: Union[UnsetType, retry.RetryStrategy] = UNSET,
            **kwargs: Any,
        ) -> Optional[AbstractResponse]:
            """
            Adds retrying logic to the method.
            """

            retry_strategy = self._retry_strategy if isinstance(_retry_strategy, UnsetType) else _retry_strategy
            if retry_strategy:
                wrapped_method = retry.retry_async(method, retry_strategy)
            else:
                wrapped_method = method

            response = await wrapped_method(self, request, **kwargs)

            return response

        return wrapper

    @retried
    @traced
    async def _send(
        self,
        request: AbstractRequest,
        response_class: Type[AbstractResponse],
        validator: Callable[..., None],
        _trace_ctx: SimpleNamespace = SimpleNamespace(),
        **kwargs: Any,
    ) -> Optional[AbstractResponse]:
        kwargs = {**self._request_args, **kwargs}
        request_text = self.json_dumper(request, cls=self.json_encoder)

        response_text = await self._request(request_text, request.is_notification, **kwargs)
        if not request.is_notification:
            response = response_class.from_json(
                self.json_loader(response_text, cls=self.json_decoder), error_cls=self.error_cls,
            )
            validator(request, response)

        else:
            if self.strict and response_text:
                raise exceptions.BaseError("unexpected response")
            response = None

        return response

    async def notify(
        self,
        method: str,
        *args: Any,
        _trace_ctx: SimpleNamespace = SimpleNamespace(),
        **kwargs: Any,
    ) -> Optional[Response]:
        """
        Makes a notification request

        :param method: method name
        :param args: method positional arguments
        :param kwargs: method named arguments
        :param _trace_ctx: tracers request context
        """

        assert not (args and kwargs), "positional and keyword arguments are mutually exclusive"

        request = self.request_class(
            id=None,
            method=method,
            params=args or kwargs,
        )
        return await self.send(request, _trace_ctx=_trace_ctx)

    async def call(
        self, method: str, *args: Any, _trace_ctx: SimpleNamespace = SimpleNamespace(), **kwargs: Any,
    ) -> Any:
        """
        Makes JSON-RPC call.

        :param method: method name
        :param args: method positional arguments
        :param kwargs: method named arguments
        :param _trace_ctx: tracers request context
        :returns: response result
        """

        assert not (args and kwargs), "positional and keyword arguments are mutually exclusive"

        request = self.request_class(
            id=next(self.id_gen_impl()),
            method=method,
            params=args or kwargs,
        )
        response = await self.send(request, _trace_ctx=_trace_ctx)

        assert response is not None, "response is not set"
        return response.result
