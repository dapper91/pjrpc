import inspect
from typing import Any, Callable, Optional

from pjrpc.common.typedefs import JsonRpcParamsT


class ValidationError(Exception):
    """
    Method parameters validation error. Raised when parameters validation failed.
    """


ExcludeFunc = Callable[[int, str, Optional[type[Any]], Optional[Any]], bool]
MethodType = Callable[..., Any]


class BaseValidatorFactory:
    """
    Base method parameters validator factory. Uses :py:func:`inspect.signature` for validation.

    :param exclude: a function that decides if the parameters must be excluded
                    from validation (useful for dependency injection)
    """

    def __init__(self, exclude: Optional[ExcludeFunc] = None):
        self._exclude = exclude

    def build(self, method: MethodType) -> 'BaseValidator':
        return BaseValidator(method, self._exclude)


class BaseValidator:
    """
    Base method parameters validator.
    """

    def __init__(self, method: MethodType, exclude: Optional[ExcludeFunc] = None):
        self._method = method
        self._exclude = exclude
        self._signature = self._build_signature(method, exclude)

    def validate_params(self, params: Optional['JsonRpcParamsT']) -> dict[str, Any]:
        """
        Validates params against method signature.

        :param params: parameters to be validated

        :raises: :py:class:`pjrpc.server.validators.ValidationError`
        :returns: bound method parameters
        """

        return self._bind(params).arguments

    def _build_signature(self, method: MethodType, exclude: Optional[ExcludeFunc]) -> inspect.Signature:
        """
        Returns method signature.

        :param method: method to get signature of
        :returns: signature
        """

        signature = inspect.signature(method)

        method_parameters: list[inspect.Parameter] = []
        for idx, param in enumerate(signature.parameters.values()):
            if exclude is None or not exclude(idx, param.name, param.annotation, param.default):
                method_parameters.append(param)

        return signature.replace(parameters=method_parameters)

    def _bind(self, params: Optional['JsonRpcParamsT']) -> inspect.BoundArguments:
        """
        Binds parameters to method.
        :param params: parameters to be bound

        :raises: ValidationError is parameters binding failed
        :returns: bound parameters
        """

        method_args = params if isinstance(params, (list, tuple)) else ()
        method_kwargs = params if isinstance(params, dict) else {}

        try:
            return self._signature.bind(*method_args, **method_kwargs)
        except TypeError as e:
            raise ValidationError(str(e)) from e
