import asyncio
import collections
import functools as ft
import json
import logging

import pjrpc
from pjrpc.common import v20, UNSET
from . import validators

logger = logging.getLogger(__package__)

default_validator = validators.base.BaseValidator()


class Method:
    """
    JSON-RPC method wrapper. Stores method and some metainformation.

    :param method: method
    :param name: method name
    :param context: context name
    """

    def __init__(self, method, name=None, context=None):
        self.method = method
        self.name = name or getattr(method, 'name', method.__name__)
        self.context = context
        self.validator, self.validator_args = getattr(method, '__pjrpc_meta__', (default_validator, {}))

    def bind(self, params, context=None):
        method_params = self.validator.validate_method(
            self.method, params, exclude=(self.context,) if self.context else (), **self.validator_args
        )

        if self.context is not None:
            method_params[self.context] = context

        return ft.partial(self.method, **method_params)


class ViewMethod(Method):

    def __init__(self, view_cls, name, context=None):
        super().__init__(view_cls, name, context)

        self.view_cls = view_cls

    def bind(self, params, context=None):
        view = self.view_cls(context) if self.context else self.view_cls()
        method = getattr(view, self.name)

        method_params = self.validator.validate_method(method, params, **self.validator_args)

        return ft.partial(method, **method_params)


class View:
    """
    Class based method handler.
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

    :param prefix:
    """

    def __init__(self, prefix=None):
        self.prefix = prefix
        self._registry = {}

    def __iter__(self):
        """

        :returns:
        """

        return iter(self._registry)

    def __getitem__(self, item):
        """

        :param item:
        :returns:
        """

        return self._registry[item]

    def get(self, item):
        """

        :param item:
        :returns:
        """

        return self._registry.get(item)

    def add(self, maybe_method=None, name=None, context=None):
        """
        Decorator

        :param maybe_method:
        :param name:
        :param context:
        :returns:
        """

        def decorator(method):
            full_name = '.'.join(filter(None, (self.prefix, name)))
            self.add_methods(Method(method, full_name, context))

            return method

        if maybe_method is None:
            return decorator
        else:
            return decorator(maybe_method)

    def add_methods(self, *methods):
        """

        :param methods:
        :returns:
        """

        for method in methods:
            if isinstance(method, Method):
                self._add_method(method.name, method)
            else:
                self.add(method)

    def view(self, maybe_view=None, context=None, prefix=None):

        def decorator(view):
            for method in view.__methods__():
                full_name = '.'.join(filter(None, (self.prefix, prefix, method.__name__)))
                self._add_method(full_name, ViewMethod(view, method.__name__, context))

            return view

        if maybe_view is None:
            return decorator
        else:
            return decorator(maybe_view)

    def merge(self, other):
        """

        :param other:
        :returns:
        """

        for name in other:
            self._add_method(name, other[name])

    def _add_method(self, name, method):
        if name in self._registry:
            logger.warning(f"method '{name}' already registered")

        self._registry[name] = method


class Dispatcher:
    """
    Method dispatcher.

    """

    def __init__(
        self,
        *,
        request_class=v20.Request,
        response_class=v20.Response,
        batch_request=v20.BatchRequest,
        batch_response=v20.BatchResponse,
        json_loader=json.loads,
        json_dumper=json.dumps,
        json_encoder=None,
        json_decoder=None,
    ):
        self._json_loader = json_loader
        self._json_dumper = json_dumper
        self._json_encoder = json_encoder or pjrpc.JSONEncoder
        self._json_decoder = json_decoder
        self._request_class = request_class
        self._response_class = response_class
        self._batch_request = batch_request
        self._batch_response = batch_response

        self._registry = MethodRegistry()

    def add(self, method, name=None, context=None):
        """

        :param method:
        :param name:
        :param context:
        :returns:
        """

        self._registry.add(method, name, context)

    def add_methods(self, *methods):
        """

        :param methods:
        :returns:
        """

        for method in methods:
            if isinstance(method, MethodRegistry):
                self._registry.merge(method)
            elif isinstance(method, Method):
                self._registry.add_methods(method)
            else:
                self._registry.add(method)

    def view(self, view):
        self._registry.view(view)

    def dispatch(self, request_text, context=None):
        try:
            request_json = self._json_loader(request_text, cls=self._json_decoder)
            if isinstance(request_json, (list, tuple)):
                request = self._batch_request.from_json(request_json)
            else:
                request = self._request_class.from_json(request_json)

        except json.JSONDecodeError as e:
            response = self._response_class(id=None, error=pjrpc.exceptions.ParseError(data=str(e)))

        except pjrpc.exceptions.DeserializationError as e:
            response = self._response_class(id=None, error=pjrpc.exceptions.InvalidRequestError(data=str(e)))

        else:
            if isinstance(request, collections.Iterable):
                # checks id duplicates
                if any(map(lambda cnt: cnt > 1, collections.Counter((req.id for req in request)).values())):
                    response = self._response_class(
                        id=None,
                        error=pjrpc.exceptions.InvalidRequestError(data="request ids are not unique")
                    )
                else:
                    response = self._batch_response(*filter(lambda resp: resp is not UNSET, (
                        await self._handle_rpc_request(request, context) for request in request
                    )))

            else:
                response = self._handle_rpc_request(request, context)

        if response is not UNSET:
            return self._json_dumper(response.to_json(), cls=self._json_encoder)

    def _handle_rpc_request(self, request, context):
        response_id, result, error = request.id, UNSET, UNSET

        try:
            result = self._handle_rpc_method(request.method, request.params, context)
        except pjrpc.exceptions.JsonRpcError as e:
            error = e
        except Exception as e:
            logger.exception("internal server error: %r", e)
            error = pjrpc.exceptions.InternalError()

        if response_id is None:
            return UNSET

        return self._response_class(id=response_id, result=result, error=self._handle_jsonrpc_error(error))

    def _handle_rpc_method(self, method_name, params, context):
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
            logger.exception("method '%s' handling error: %r", method_name, e)
            raise pjrpc.exceptions.ServerError() from e

    def _handle_jsonrpc_error(self, error):
        if error and error.data:
            error.data = str(error.data)

        return error


class AsyncDispatcher(Dispatcher):
    """
    Asynchronous method dispatcher.
    """

    async def dispatch(self, request_text, context=None):
        try:
            request_json = self._json_loader(request_text, cls=self._json_decoder)
            if isinstance(request_json, (list, tuple)):
                request = self._batch_request.from_json(request_json)
            else:
                request = self._request_class.from_json(request_json)

        except json.JSONDecodeError as e:
            response = self._response_class(id=None, error=pjrpc.exceptions.ParseError(data=str(e)))

        except pjrpc.exceptions.DeserializationError as e:
            response = self._response_class(id=None, error=pjrpc.exceptions.InvalidRequestError(data=str(e)))

        else:
            if isinstance(request, collections.Iterable):
                # checks id duplicates
                if any(map(lambda cnt: cnt > 1, collections.Counter((req.id for req in request)).values())):
                    response = self._response_class(
                        id=None,
                        error=pjrpc.exceptions.InvalidRequestError(data="request ids are not unique")
                    )
                else:
                    response = self._batch_response(*filter(lambda resp: resp is not UNSET, (
                        await self._handle_rpc_request(request, context) for request in request
                    )))

            else:
                response = await self._handle_rpc_request(request, context)

        if response is not UNSET:
            return self._json_dumper(response.to_json(), cls=self._json_encoder)

    async def _handle_rpc_request(self, request, context):
        response_id, result, error = request.id, UNSET, UNSET

        try:
            result = await self._handle_rpc_method(request.method, request.params, context)
        except pjrpc.exceptions.JsonRpcError as e:
            error = e
        except Exception as e:
            logger.exception("internal server error: %r", e)
            error = pjrpc.exceptions.InternalError()

        if response_id is None:
            return UNSET

        return self._response_class(id=response_id, result=result, error=self._handle_jsonrpc_error(error))

    async def _handle_rpc_method(self, method_name, params, context):
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
            logger.exception("method '%s' handling error: %r", method_name, e)
            raise pjrpc.exceptions.ServerError() from e
