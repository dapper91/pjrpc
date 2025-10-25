import abc
import asyncio
import functools as ft
import json
import logging
import warnings
from typing import Any, Awaitable, Callable, Concatenate, Generic, ItemsView, Iterable, Iterator, KeysView, Optional
from typing import ParamSpec, Self, TypeVar, Union, ValuesView

import pjrpc
from pjrpc.common import UNSET, AbstractResponse, BatchRequest, BatchResponse, MaybeSet, Request, Response, UnsetType
from pjrpc.common.typedefs import JsonRpcParamsT
from pjrpc.server import utils
from pjrpc.server.typedefs import AsyncMiddlewareType, MiddlewareType

from . import validators

logger = logging.getLogger(__package__)


FunctionType = Callable[..., Any]
BoundMethod = Callable[[], Any]

FuncParamsT = ParamSpec('FuncParamsT')
FuncResultT = TypeVar('FuncResultT')


class Method(Generic[FuncParamsT, FuncResultT]):
    """
    JSON-RPC method wrapper. Stores method itself and some metainformation.

    :param func: method function
    :param name: method name
    :param pass_context: context name
    :param validator_factory: method validator factory
    :param metadata: method metadata
    """

    def __init__(
        self,
        func: Callable[FuncParamsT, FuncResultT],
        name: Optional[str] = None,
        *,
        pass_context: Union[bool, str] = False,
        validator_factory: Optional[validators.BaseValidatorFactory] = None,
        metadata: Iterable[Any] = (),
    ):
        self.func = func
        self.name = name or func.__name__
        self.pass_context = pass_context
        self.metadata = list(metadata)

        if isinstance(self.pass_context, bool):
            if self.pass_context:
                exclude = utils.exclude_positional_param(0)
            else:
                exclude = None
        elif isinstance(self.pass_context, str):
            exclude = utils.exclude_named_param(self.pass_context)
        else:
            raise AssertionError("unreachable")

        validator_factory = validator_factory or validators.BaseValidatorFactory(exclude=exclude)
        self.validator = validator_factory.build(func)

    def __call__(self, *args: FuncParamsT.args, **kwargs: FuncParamsT.kwargs) -> FuncResultT:
        return self.func(*args, **kwargs)

    def bind(self, params: Optional[JsonRpcParamsT], context: Optional[Any] = None) -> BoundMethod:
        method_args: list[Any] = []
        method_kwargs = self.validator.validate_params(params)

        method_args, method_kwargs = self._prepare_method_args(method_args, method_kwargs, context)

        return ft.partial(self.func, *method_args, **method_kwargs)

    def _prepare_method_args(
        self,
        args: list[Any],
        kwargs: dict[str, Any],
        context: Optional[Any],
    ) -> tuple[list[Any], dict[str, Any]]:
        if isinstance(self.pass_context, bool):
            if self.pass_context:
                args.append(context)
        elif isinstance(self.pass_context, str):
            kwargs[self.pass_context] = context
        else:
            raise AssertionError("unreachable")

        return args, kwargs


MetadataProcessorT = Callable[[Method[Any, Any]], Method[Any, Any]]


class MethodRegistry:
    """
    Method registry.
    """

    def __init__(
        self,
        validator_factory: Optional[validators.BaseValidatorFactory] = None,
        metadata: Iterable[Any] = (),
        metadata_processors: Iterable[MetadataProcessorT] = (),
    ) -> None:
        self._validator_factory = validator_factory
        self._metadata = list(metadata)
        self._metadata_processors = list(metadata_processors)
        self._registry: dict[str, Method[Any, Any]] = {}

    def __iter__(self) -> Iterator[str]:
        """
        Returns registry method iterator.
        """

        return iter(self._registry)

    def __getitem__(self, item: str) -> Method[Any, Any]:
        """
        Returns a method from the registry by name.

        :param item: method name
        :returns: found method
        :raises: KeyError
        """

        return self._registry[item]

    def items(self) -> ItemsView[str, Method[Any, Any]]:
        return self._registry.items()

    def keys(self) -> KeysView[str]:
        return self._registry.keys()

    def values(self) -> ValuesView[Method[Any, Any]]:
        return self._registry.values()

    def get(self, item: str) -> Optional[Method[Any, Any]]:
        """
        Returns a method from the registry by name.

        :param item: method name
        :returns: found method or `None`
        """

        return self._registry.get(item)

    def merge(self, other: 'MethodRegistry') -> Self:
        for method in other.values():
            self._add_method(method)

        return self

    def add(
        self,
        name: Optional[str] = None,
        *,
        pass_context: Union[bool, str] = False,
        metadata: Iterable[Any] = (),
    ) -> Callable[[Callable[FuncParamsT, FuncResultT]], Callable[FuncParamsT, FuncResultT]]:
        """
        Decorator adding decorated method to the registry.

        :param name: method name to be used instead of `__name__` attribute
        :param pass_context: pass application context if supported
        :param metadata: method metadata

        :returns: decorated method or decorator
        """

        def decorator(func: Callable[FuncParamsT, FuncResultT]) -> Callable[FuncParamsT, FuncResultT]:
            self._add_function(
                func,
                name,
                pass_context=pass_context,
                metadata=metadata,
            )

            return func

        return decorator

    def add_method(
        self,
        method: FunctionType,
        name: Optional[str] = None,
        *,
        pass_context: Union[bool, str] = False,
        metadata: Iterable[Any] = (),
    ) -> Self:
        """
        Adds the method to the registry.

        :param method: method to be added
        :param name: method name to be used instead of `__name__` attribute
        :param pass_context: pass application context if supported
        :param metadata: method metadata

        :returns: decorated method or decorator
        """

        self._add_function(
            method,
            name,
            pass_context=pass_context,
            metadata=metadata,
        )

        return self

    def _add_function(
        self,
        func: FunctionType,
        name: Optional[str] = None,
        pass_context: Union[bool, str] = False,
        metadata: Iterable[Any] = (),
    ) -> None:
        self._add_method(
            Method(
                func,
                name,
                pass_context=pass_context,
                metadata=metadata,
                validator_factory=self._validator_factory,
            ),
        )

    def _add_method(self, method: Method[Any, Any]) -> None:
        if method.name in self._registry:
            warnings.warn(f"method '{method.name}' already registered")

        method.metadata.extend(self._metadata)
        for metadata_processor in self._metadata_processors:
            method = metadata_processor(method)

        self._registry[method.name] = method


class JSONEncoder(pjrpc.JSONEncoder):
    """
    Server JSON encoder. All custom server encoders should be inherited from it.
    """

    def default(self, o: Any) -> Any:
        if isinstance(o, validators.base.ValidationError):
            return [err for err in o.args]

        return super().default(o)


def extract_error_codes(response: AbstractResponse) -> tuple[int, ...]:
    if isinstance(response, BatchResponse):
        return (response.error.code,) if response.error else tuple(r.error.code if r.error else 0 for r in response)
    elif isinstance(response, Response):
        return (response.error.code if response.error else 0,)
    else:
        raise AssertionError("unreachable")


class BaseDispatcher:
    """
    Method dispatcher.

    :param request_class: JSON-RPC request class
    :param response_class: JSON-RPC response class
    :param batch_request: JSON-RPC batch request class
    :param batch_response: JSON-RPC batch response class
    :param json_loader: request json loader
    :param json_dumper: response json dumper
    :param json_encoder: response json encoder
    :param json_decoder: request json decoder
    :param middlewares: request middlewares
    """

    def __init__(
        self,
        *,
        request_class: type[Request] = Request,
        response_class: type[Response] = Response,
        batch_request: type[BatchRequest] = BatchRequest,
        batch_response: type[BatchResponse] = BatchResponse,
        json_loader: Callable[..., Any] = json.loads,
        json_dumper: Callable[..., str] = json.dumps,
        json_encoder: type[JSONEncoder] = JSONEncoder,
        json_decoder: Optional[type[json.JSONDecoder]] = None,
        middlewares: Iterable[Callable[..., Any]] = (),
    ):
        self._json_loader = json_loader
        self._json_dumper = json_dumper
        self._json_encoder = json_encoder
        self._json_decoder = json_decoder
        self._request_class = request_class
        self._response_class = response_class
        self._batch_request = batch_request
        self._batch_response = batch_response
        self._middlewares = list(middlewares)

        self._registry = MethodRegistry()

    @property
    def registry(self) -> MethodRegistry:
        return self._registry

    def add_methods(self, registry: MethodRegistry) -> Self:
        self._registry.merge(registry)
        return self


HandlerParams = ParamSpec('HandlerParams')
HandlerResult = TypeVar('HandlerResult')


class Executor(abc.ABC):
    """
    Method executor.
    """

    @abc.abstractmethod
    def execute(
        self,
        handler: Callable[Concatenate[Request, HandlerParams], HandlerResult],
        /,
        requests: Iterable[Request],
        *args: HandlerParams.args,
        **kwargs: HandlerParams.kwargs,
    ) -> Iterable[HandlerResult]:
        pass


class BasicExecutor(Executor):
    """
    Sequential in-thread method executor
    """

    def execute(
        self,
        handler: Callable[Concatenate[Request, HandlerParams], HandlerResult],
        /,
        requests: Iterable[Request],
        *args: HandlerParams.args,
        **kwargs: HandlerParams.kwargs,
    ) -> Iterable[HandlerResult]:
        return list(handler(request, *args, **kwargs) for request in requests)


ContextType = TypeVar('ContextType')


class Dispatcher(BaseDispatcher, Generic[ContextType]):
    """
    Synchronous method dispatcher.
    """

    def __init__(
        self,
        *,
        executor: Optional[Executor] = None,
        json_loader: Callable[..., Any] = json.loads,
        json_dumper: Callable[..., str] = json.dumps,
        json_encoder: type[JSONEncoder] = JSONEncoder,
        json_decoder: Optional[type[json.JSONDecoder]] = None,
        middlewares: Iterable['MiddlewareType[ContextType]'] = (),
        max_batch_size: Optional[int] = None,
    ):
        super().__init__(
            json_loader=json_loader,
            json_dumper=json_dumper,
            json_encoder=json_encoder,
            json_decoder=json_decoder,
            middlewares=middlewares,
        )
        self._max_batch_size = max_batch_size
        self._executor = executor or BasicExecutor()

        self._request_handler = self._wrap_handle_request()

    def dispatch(self, request_text: str, context: ContextType) -> Optional[tuple[str, tuple[int, ...]]]:
        """
        Deserializes request, dispatches it to the required method and serializes the result.

        :param request_text: request text representation
        :param context: application context (if supported)
        :return: response text representation and error codes
        """

        logger.getChild('raw_request').debug("request received: %s", request_text)

        response: MaybeSet[AbstractResponse]
        try:
            request_json = self._json_loader(request_text, cls=self._json_decoder)
            request: Union[Request, BatchRequest]
            if isinstance(request_json, (list, tuple)):
                request = self._batch_request.from_json(request_json)
            else:
                request = self._request_class.from_json(request_json)

        except json.JSONDecodeError as e:
            response = self._response_class(id=None, error=pjrpc.exceptions.ParseError(data=str(e)))

        except (pjrpc.exceptions.DeserializationError, pjrpc.exceptions.IdentityError) as e:
            response = self._response_class(id=None, error=pjrpc.exceptions.InvalidRequestError(data=str(e)))

        else:
            if isinstance(request, BatchRequest):
                if self._max_batch_size and len(request) > self._max_batch_size:
                    response = self._response_class(
                        id=None,
                        error=pjrpc.exceptions.InvalidRequestError(data="batch too large"),
                    )
                else:
                    responses = (
                        resp for resp in self._executor.execute(self._request_handler, request, context)
                        if not isinstance(resp, UnsetType)
                    )
                    response = self._batch_response(tuple(responses))
            else:
                response = self._request_handler(request, context)

        if not isinstance(response, UnsetType):
            response_text = self._json_dumper(response.to_json(), cls=self._json_encoder)
            logger.getChild('raw_response').debug("response prepared: %s", response_text)

            return response_text, extract_error_codes(response)

        return None

    def add_middlewares(self, *middlewares: MiddlewareType[ContextType], before: bool = False) -> None:
        if before:
            self._middlewares = list(middlewares) + self._middlewares
        else:
            self._middlewares = self._middlewares + list(middlewares)

        self._request_handler = self._wrap_handle_request()

    def _wrap_handle_request(self) -> Callable[[Request, ContextType], MaybeSet[Response]]:
        request_handler = self._handle_request
        for middleware in reversed(self._middlewares):
            request_handler = ft.partial(middleware, handler=request_handler)

        return request_handler

    def _handle_request(self, request: Request, /, context: ContextType) -> MaybeSet[Response]:
        try:
            return self._handle_rpc_request(request, context)
        except pjrpc.exceptions.JsonRpcError as e:
            logger.info("method execution error %s(%r): %r", request.method, request.params, e)
            error = e

        except Exception as e:
            logger.exception("internal server error: %r", e)
            error = pjrpc.exceptions.InternalError()

        if request.id is None:
            return UNSET

        return self._response_class(id=request.id, error=error)

    def _handle_rpc_request(self, request: Request, context: ContextType) -> MaybeSet[Response]:
        result = self._handle_rpc_method(request.method, request.params, context)
        if request.id is None:
            return UNSET

        return self._response_class(id=request.id, result=result)

    def _handle_rpc_method(
        self,
        method_name: str,
        params: Optional[JsonRpcParamsT],
        context: ContextType,
    ) -> Any:
        method = self._registry.get(method_name)
        if method is None:
            raise pjrpc.exceptions.MethodNotFoundError(data=f"method '{method_name}' not found")

        try:
            bound_method = method.bind(params, context=context)
        except validators.ValidationError as e:
            raise pjrpc.exceptions.InvalidParamsError(data=e) from e

        try:
            return bound_method()

        except pjrpc.exceptions.JsonRpcError:
            raise

        except Exception as e:
            logger.exception("method unhandled exception %s(%r): %r", method_name, params, e)
            raise pjrpc.exceptions.ServerError() from e


class AsyncExecutor(abc.ABC):
    """
    Asynchronous method executor.
    """

    @abc.abstractmethod
    async def execute(
        self,
        handler: Callable[Concatenate[Request, HandlerParams], Awaitable[HandlerResult]],
        /,
        requests: Iterable[Request],
        *args: HandlerParams.args,
        **kwargs: HandlerParams.kwargs,
    ) -> Iterable[HandlerResult]:
        pass


class BasicAsyncExecutor(AsyncExecutor):
    """
    Sequential asynchronous method executor
    """

    async def execute(
        self,
        handler: Callable[Concatenate[Request, HandlerParams], Awaitable[HandlerResult]],
        /,
        requests: Iterable[Request],
        *args: HandlerParams.args,
        **kwargs: HandlerParams.kwargs,
    ) -> Iterable[HandlerResult]:
        return [await handler(request, *args, **kwargs) for request in requests]


class ParallelAsyncExecutor(AsyncExecutor):
    """
    Parallel asynchronous method executor
    """

    async def execute(
        self,
        handler: Callable[Concatenate[Request, HandlerParams], Awaitable[HandlerResult]],
        /,
        requests: Iterable[Request],
        *args: HandlerParams.args,
        **kwargs: HandlerParams.kwargs,
    ) -> Iterable[HandlerResult]:
        return list(await asyncio.gather(*(handler(request, *args, **kwargs) for request in requests)))


class AsyncDispatcher(BaseDispatcher, Generic[ContextType]):
    """
    Asynchronous method dispatcher.
    """

    def __init__(
        self,
        *,
        executor: Optional[AsyncExecutor] = None,
        json_loader: Callable[..., Any] = json.loads,
        json_dumper: Callable[..., str] = json.dumps,
        json_encoder: type[JSONEncoder] = JSONEncoder,
        json_decoder: Optional[type[json.JSONDecoder]] = None,
        middlewares: Iterable[AsyncMiddlewareType[ContextType]] = (),
        max_batch_size: Optional[int] = None,
    ):
        super().__init__(
            json_loader=json_loader,
            json_dumper=json_dumper,
            json_encoder=json_encoder,
            json_decoder=json_decoder,
            middlewares=middlewares,
        )
        self._max_batch_size = max_batch_size
        self._executor = executor or BasicAsyncExecutor()

        self._request_handler = self._wrap_handle_request()

    async def dispatch(self, request_text: str, context: ContextType) -> Optional[tuple[str, tuple[int, ...]]]:
        """
        Deserializes request, dispatches it to the required method and serializes the result.

        :param request_text: request text representation
        :param context: application context (if supported)
        :return: response text representation and error codes
        """

        logger.getChild('request').debug("request received: %s", request_text)

        response: MaybeSet[AbstractResponse]
        try:
            request_json = self._json_loader(request_text, cls=self._json_decoder)
            request: Union[Request, BatchRequest]
            if isinstance(request_json, (list, tuple)):
                request = self._batch_request.from_json(request_json)
            else:
                request = self._request_class.from_json(request_json)

        except json.JSONDecodeError as e:
            response = self._response_class(id=None, error=pjrpc.exceptions.ParseError(data=str(e)))

        except (pjrpc.exceptions.DeserializationError, pjrpc.exceptions.IdentityError) as e:
            response = self._response_class(id=None, error=pjrpc.exceptions.InvalidRequestError(data=str(e)))

        else:
            if isinstance(request, BatchRequest):
                if self._max_batch_size and len(request) > self._max_batch_size:
                    response = self._response_class(
                        id=None,
                        error=pjrpc.exceptions.InvalidRequestError(data="batch too large"),
                    )
                else:
                    responses = (
                        resp for resp in await self._executor.execute(self._request_handler, request, context)
                        if not isinstance(resp, UnsetType)
                    )
                    response = self._batch_response(tuple(responses))
            else:
                response = await self._request_handler(request, context)

        if not isinstance(response, UnsetType):
            response_text = self._json_dumper(response.to_json(), cls=self._json_encoder)
            logger.getChild('response').debug("response sent: %s", response_text)

            return response_text, extract_error_codes(response)

        return None

    def add_middlewares(self, *middlewares: AsyncMiddlewareType[ContextType], before: bool = False) -> None:
        if before:
            self._middlewares = list(middlewares) + self._middlewares
        else:
            self._middlewares = self._middlewares + list(middlewares)

        self._request_handler = self._wrap_handle_request()

    def _wrap_handle_request(self) -> Callable[[Request, ContextType], Awaitable[MaybeSet[Response]]]:
        request_handler = self._handle_request
        for middleware in reversed(self._middlewares):
            request_handler = ft.partial(middleware, handler=request_handler)

        return request_handler

    async def _handle_request(self, request: Request, context: ContextType) -> MaybeSet[Response]:
        try:
            return await self._handle_rpc_request(request, context)
        except pjrpc.exceptions.JsonRpcError as e:
            logger.info("method execution error %s(%r): %r", request.method, request.params, e)
            error = e

        except Exception as e:
            logger.exception("internal server error: %r", e)
            error = pjrpc.exceptions.InternalError()

        if request.id is None:
            return UNSET

        return self._response_class(id=request.id, error=error)

    async def _handle_rpc_request(self, request: Request, context: ContextType) -> MaybeSet[Response]:
        result = await self._handle_rpc_method(request.method, request.params, context)
        if request.id is None:
            return UNSET

        return self._response_class(id=request.id, result=result)

    async def _handle_rpc_method(
        self, method_name: str, params: Optional[JsonRpcParamsT], context: ContextType,
    ) -> Any:
        method = self._registry.get(method_name)
        if method is None:
            raise pjrpc.exceptions.MethodNotFoundError(data=f"method '{method_name}' not found")

        try:
            bound_method = method.bind(params, context=context)
        except validators.ValidationError as e:
            raise pjrpc.exceptions.InvalidParamsError(data=e) from e

        try:
            result = bound_method()
            if asyncio.iscoroutine(result):
                result = await result

            return result

        except pjrpc.exceptions.JsonRpcError:
            raise

        except Exception as e:
            logger.exception("method unhandled exception %s(%r): %r", method_name, params, e)
            raise pjrpc.exceptions.ServerError() from e
