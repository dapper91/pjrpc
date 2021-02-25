import asyncio
import collections
import functools as ft
import json
import itertools as it
import logging
from typing import Any, Callable, Dict, List, Optional, Type, Iterator, Iterable, Union

import pjrpc
from pjrpc.common import v20, BatchRequest, BatchResponse, Request, Response, UNSET, UnsetType
from . import validators

logger = logging.getLogger(__package__)

default_validator = validators.base.BaseValidator()


class Method:
    """
    JSON-RPC method wrapper. Stores method itself and some metainformation.

    :param method: method
    :param name: method name
    :param context: context name
    """

    def __init__(self, method: Callable, name: Optional[str] = None, context: Optional[Any] = None):
        self.method = method
        self.name = name or getattr(method, 'name', method.__name__)
        self.context = context
        self.validator, self.validator_args = getattr(method, '__pjrpc_meta__', (default_validator, {}))

    def bind(self, params: Optional[Union[list, dict]], context: Optional[Any] = None) -> Callable:
        method_params = self.validator.validate_method(
            self.method, params, exclude=(self.context,) if self.context else (), **self.validator_args
        )

        if self.context is not None:
            method_params[self.context] = context

        return ft.partial(self.method, **method_params)


class ViewMethod(Method):
    """
    View method.

    :param view_cls: view class
    :param name: view class method name
    :param context: context name
    """

    def __init__(self, view_cls: Type['ViewMixin'], name: str, context: Optional[Any] = None):
        super().__init__(view_cls, name, context)

        self.view_cls = view_cls

    def bind(self, params: Optional[Union[list, dict]], context: Optional[Any] = None) -> Callable:
        view = self.view_cls(context) if self.context else self.view_cls()
        method = getattr(view, self.name)

        method_params = self.validator.validate_method(method, params, **self.validator_args)

        return ft.partial(method, **method_params)


class ViewMixin:
    """
    Class based method handler mixin.
    """

    @classmethod
    def __methods__(cls):
        for attr_name in filter(lambda name: not name.startswith('_'), dir(cls)):
            attr = getattr(cls, attr_name)
            if callable(attr):
                yield attr


class MethodRegistry:
    """
    Method registry.

    :param prefix: method name prefix to be used for naming containing methods
    """

    def __init__(self, prefix: Optional[str] = None):
        self._prefix = prefix
        self._registry: Dict[str, Method] = {}

    def __iter__(self) -> Iterator[str]:
        """
        Returns registry method iterator.
        """

        return iter(self._registry)

    def __getitem__(self, item: str) -> Method:
        """
        Returns a method from the registry by name.

        :param item: method name
        :returns: found method
        :raises: KeyError
        """

        return self._registry[item]

    def get(self, item: str) -> Optional[Method]:
        """
        Returns a method from the registry by name.

        :param item: method name
        :returns: found method or `None`
        """

        return self._registry.get(item)

    def add(
        self, maybe_method: Optional[Callable] = None, name: Optional[str] = None, context: Optional[Any] = None,
    ) -> Callable:
        """
        Decorator adding decorated method to the registry.

        :param maybe_method: method or `None`
        :param name: method name to be used instead of `__name__` attribute
        :param context: parameter name to be used as an application context
        :returns: decorated method or decorator
        """

        def decorator(method: Callable) -> Callable:
            full_name = '.'.join(filter(None, (self._prefix, name or getattr(method, 'name', method.__name__))))
            self.add_methods(Method(method, full_name, context))

            return method

        if maybe_method is None:
            return decorator
        else:
            return decorator(maybe_method)

    def add_methods(self, *methods: Union[Callable, Method]) -> None:
        """
        Adds methods to the registry.

        :param methods: methods to be added. Each one can be an instance of :py:class:`pjrpc.server.Method`
                        or plain method
        """

        for method in methods:
            if isinstance(method, Method):
                self._add_method(method.name, method)
            else:
                self.add(method)

    def view(
        self, maybe_view: Optional[Type[ViewMixin]] = None, context: Optional[Any] = None, prefix: Optional[str] = None,
    ) -> Union[ViewMixin, Callable]:
        """
        Methods view decorator.

        :param maybe_view: view class instance or `None`
        :param context: application context name
        :param prefix: view methods prefix
        :return: decorator or decorated view
        """

        def decorator(view: Type[ViewMixin]) -> Type[ViewMixin]:
            for method in view.__methods__():
                full_name = '.'.join(filter(None, (self._prefix, prefix, method.__name__)))
                self._add_method(full_name, ViewMethod(view, method.__name__, context))

            return view

        # maybe_view's type depends on the usage of the decorator.  It's a View
        # if it's used as `@view` but ``None`` if used as `@view()`.
        if maybe_view is None:
            return decorator
        else:
            return decorator(maybe_view)

    def merge(self, other: 'MethodRegistry') -> None:
        """
        Merges two registries.

        :param other: registry to be merged in the current one
        """

        for name in other:
            self._add_method(name, other[name])

    def _add_method(self, name: str, method: Method) -> None:
        if name in self._registry:
            logger.warning(f"method '{name}' already registered")

        self._registry[name] = method


class JSONEncoder(pjrpc.JSONEncoder):
    """
    Server JSON encoder. All custom server encoders should be inherited from it.
    """

    def default(self, o: Any) -> Any:
        if isinstance(o, validators.base.ValidationError):
            return [err for err in o.args]

        return super().default(o)


class Dispatcher:
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
    """

    def __init__(
        self,
        *,
        request_class: Type[Request] = v20.Request,
        response_class: Type[Response] = v20.Response,
        batch_request: Type[BatchRequest] = v20.BatchRequest,
        batch_response: Type[BatchResponse] = v20.BatchResponse,
        json_loader: Callable = json.loads,
        json_dumper: Callable = json.dumps,
        json_encoder: Type[JSONEncoder] = JSONEncoder,
        json_decoder: Optional[Type[json.JSONDecoder]] = None,
        middlewares: Iterable[Callable] = (),
        error_handlers: Dict[Union[None, int, Exception], List[Callable]] = {},
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
        self._error_handlers = error_handlers

        self._registry = MethodRegistry()

    def add(self, method: Callable, name: Optional[str] = None, context: Optional[Any] = None) -> None:
        """
        Adds method to the registry.

        :param method: method
        :param name: method name
        :param context: application context name
        """

        self._registry.add(method, name, context)

    def add_methods(self, *methods: Union[MethodRegistry, Method, Callable]) -> None:
        """
        Adds methods to the registry.

        :param methods: method list. Each method may be an instance of :py:class:`pjrpc.server.MethodRegistry`,
                        :py:class:`pjrpc.server.Method` or plain function
        """

        for method in methods:
            if isinstance(method, MethodRegistry):
                self._registry.merge(method)
            elif isinstance(method, Method):
                self._registry.add_methods(method)
            else:
                self._registry.add(method)

    def view(self, view: Type[ViewMixin]) -> None:
        """
        Adds class based view to the registry.

        :param view: view to be added
        """

        self._registry.view(view)

    def dispatch(self, request_text: str, context: Optional[Any] = None) -> Optional[str]:
        """
        Deserializes request, dispatches it to the required method and serializes the result.

        :param request_text: request text representation
        :param context: application context (if supported)
        :return: response text representation
        """

        logger.debug("request received: %s", request_text)

        try:
            request_json = self._json_loader(request_text, cls=self._json_decoder)
            if isinstance(request_json, (list, tuple)):
                request = self._batch_request.from_json(request_json)
            else:
                request = self._request_class.from_json(request_json)

        except json.JSONDecodeError as e:
            response = self._response_class(id=None, error=pjrpc.exceptions.ParseError(data=str(e)))

        except (pjrpc.exceptions.DeserializationError, pjrpc.exceptions.IdentityError) as e:
            response = self._response_class(id=None, error=pjrpc.exceptions.InvalidRequestError(data=str(e)))

        else:
            if isinstance(request, collections.abc.Iterable):
                response = self._batch_response(
                    *filter(
                        lambda resp: resp is not UNSET, (
                            self._handle_request(request, context) for request in request
                        ),
                    )
                )

            else:
                response = self._handle_request(request, context)

        if response is not UNSET:
            response_text = self._json_dumper(response.to_json(), cls=self._json_encoder)
            logger.debug("response sent: %s", response_text)

            return response_text

    def _handle_request(self, request: Request, context: Optional[Any]) -> Union[UnsetType, Response]:
        try:
            handler = self._handle_rpc_request

            for middleware in reversed(self._middlewares):
                handler = ft.partial(middleware, handler=handler)

            return handler(request, context)

        except pjrpc.exceptions.JsonRpcError as e:
            logger.info("method execution error %s(%r): %r", request.method, request.params, e)
            error = e

        except Exception as e:
            logger.exception("internal server error: %r", e)
            error = pjrpc.exceptions.InternalError()

        for handler in it.chain(self._error_handlers.get(None, []), self._error_handlers.get(error.code, [])):
            error = handler(request, context, error)

        if request.id is None:
            return UNSET

        return self._response_class(id=request.id, error=error)

    def _handle_rpc_request(self, request: Request, context: Optional[Any]) -> Union[UnsetType, Response]:
        result = self._handle_rpc_method(request.method, request.params, context)
        if request.id is None:
            return UNSET

        return self._response_class(id=request.id, result=result)

    def _handle_rpc_method(self, method_name: str, params: Optional[Union[list, dict]], context: Optional[Any]) -> Any:
        method = self._registry.get(method_name)
        if method is None:
            raise pjrpc.exceptions.MethodNotFoundError(data=f"method '{method_name}' not found")

        try:
            method = method.bind(params, context=context)
        except validators.ValidationError as e:
            raise pjrpc.exceptions.InvalidParamsError(data=e) from e

        try:
            return method()

        except pjrpc.exceptions.JsonRpcError:
            raise

        except Exception as e:
            logger.exception("method unhandled exception %s(%r): %r", method_name, params, e)
            raise pjrpc.exceptions.ServerError() from e


class AsyncDispatcher(Dispatcher):
    """
    Asynchronous method dispatcher.
    """

    async def dispatch(self, request_text: str, context: Optional[Any] = None) -> Optional[str]:
        """
        Deserializes request, dispatches it to the required method and serializes the result.

        :param request_text: request text representation
        :param context: application context (if supported)
        :return: response text representation
        """

        logger.debug("request received: %s", request_text)

        try:
            request_json = self._json_loader(request_text, cls=self._json_decoder)
            if isinstance(request_json, (list, tuple)):
                request = self._batch_request.from_json(request_json)
            else:
                request = self._request_class.from_json(request_json)

        except json.JSONDecodeError as e:
            response = self._response_class(id=None, error=pjrpc.exceptions.ParseError(data=str(e)))

        except (pjrpc.exceptions.DeserializationError, pjrpc.exceptions.IdentityError) as e:
            response = self._response_class(id=None, error=pjrpc.exceptions.InvalidRequestError(data=str(e)))

        else:
            if isinstance(request, collections.Iterable):
                response = self._batch_response(
                    *filter(
                        lambda resp: resp is not UNSET, await asyncio.gather(
                            *(self._handle_request(request, context) for request in request)
                        ),
                    )
                )

            else:
                response = await self._handle_request(request, context)

        if response is not UNSET:
            response_text = self._json_dumper(response.to_json(), cls=self._json_encoder)
            logger.debug("response sent: %s", response_text)

            return response_text

    async def _handle_request(self, request: Request, context: Optional[Any]) -> Union[UnsetType, Response]:
        try:
            handler = self._handle_rpc_request

            for middleware in reversed(self._middlewares):
                handler = ft.partial(middleware, handler=handler)

            return await handler(request, context)

        except pjrpc.exceptions.JsonRpcError as e:
            logger.info("method execution error %s(%r): %r", request.method, request.params, e)
            error = e

        except Exception as e:
            logger.exception("internal server error: %r", e)
            error = pjrpc.exceptions.InternalError()

        for handler in it.chain(self._error_handlers.get(None, []), self._error_handlers.get(error.code, [])):
            error = await handler(request, context, error)

        if request.id is None:
            return UNSET

        return self._response_class(id=request.id, error=error)

    async def _handle_rpc_request(self, request: Request, context: Optional[Any]) -> Union[UnsetType, Response]:
        result = await self._handle_rpc_method(request.method, request.params, context)
        if request.id is None:
            return UNSET

        return self._response_class(id=request.id, result=result)

    async def _handle_rpc_method(
        self, method_name: str, params: Optional[Union[list, dict]], context: Optional[Any],
    ) -> Any:
        method = self._registry.get(method_name)
        if method is None:
            raise pjrpc.exceptions.MethodNotFoundError(data=f"method '{method_name}' not found")

        try:
            method = method.bind(params, context=context)
        except validators.ValidationError as e:
            raise pjrpc.exceptions.InvalidParamsError(data=e) from e

        try:
            result = method()
            if asyncio.iscoroutine(result):
                result = await result

            return result

        except pjrpc.exceptions.JsonRpcError:
            raise

        except Exception as e:
            logger.exception("method unhandled exception %s(%r): %r", method_name, params, e)
            raise pjrpc.exceptions.ServerError() from e
