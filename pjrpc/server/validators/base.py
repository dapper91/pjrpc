import functools as ft
import inspect
from typing import Any, Dict, Iterable, List, Optional, Tuple

from pjrpc.common.typedefs import JsonRpcParams, MethodType
from pjrpc.server import utils
from pjrpc.server.typedefs import ExcludeFunc


class ValidationError(Exception):
    """
    Method parameters validation error. Raised when parameters validation failed.
    """


class BaseValidator:
    """
    Base method parameters validator. Uses :py:func:`inspect.signature` for validation.

    :param exclude_param: a function that decides if the parameters must be excluded
                          from validation (useful for dependency injection)
    """

    def __init__(self, exclude_param: Optional[ExcludeFunc] = None):
        self._exclude_param = exclude_param or (lambda *args: False)

    def validate(self, maybe_method: Optional[MethodType] = None, **kwargs: Any) -> MethodType:
        """
        Decorator marks a method the parameters of which to be validated when calling it using JSON-RPC protocol.

        :param maybe_method: method the parameters of which to be validated or ``None`` if called as @validate(...)
        :param kwargs: validator arguments
        """

        def decorator(method: MethodType) -> MethodType:
            utils.set_meta(method, validator=self, validator_args=kwargs)
            return method

        # maybe_method's type depends on the usage of the decorator.  It's a function
        # if it's used as `@validate` but ``None`` if used as `@validate()`.
        if maybe_method is None:
            return decorator
        else:
            return decorator(maybe_method)

    def validate_method(
        self, method: MethodType, params: Optional['JsonRpcParams'], exclude: Iterable[str] = (), **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Validates params against method signature.

        :param method: method to validate parameters against
        :param params: parameters to be validated
        :param exclude: parameter names to be excluded from validation
        :param kwargs: additional validator arguments

        :raises: :py:class:`pjrpc.server.validators.ValidationError`
        :returns: bound method parameters
        """

        signature = self.signature(method, tuple(exclude))
        return self.bind(signature, params).arguments

    def bind(self, signature: inspect.Signature, params: Optional['JsonRpcParams']) -> inspect.BoundArguments:
        """
        Binds parameters to method.
        :param signature: method to bind parameters to
        :param params: parameters to be bound

        :raises: ValidationError is parameters binding failed
        :returns: bound parameters
        """

        method_args = params if isinstance(params, (list, tuple)) else ()
        method_kwargs = params if isinstance(params, dict) else {}

        try:
            return signature.bind(*method_args, **method_kwargs)
        except TypeError as e:
            raise ValidationError(str(e)) from e

    @ft.lru_cache(None)
    def signature(self, method: MethodType, exclude: Tuple[str, ...]) -> inspect.Signature:
        """
        Returns method signature.

        :param method: method to get signature of
        :param exclude: parameters to be excluded
        :returns: signature
        """

        signature = inspect.signature(method)

        method_parameters: List[inspect.Parameter] = []
        for param in signature.parameters.values():
            if param.name not in exclude and not self._exclude_param(param.name, param.annotation, param.default):
                method_parameters.append(param)

        return signature.replace(parameters=method_parameters)
