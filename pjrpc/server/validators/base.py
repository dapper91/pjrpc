import functools as ft
import inspect


class ValidationError(Exception):
    """
    Method parameters validation error. Raised when parameters validation failed.
    """


class BaseValidator:
    """
    Base method parameters validator. Uses :py:func:`inspect.signature` for validation.
    """

    def validate(self, maybe_method=None, **kwargs):
        """
        Decorator marks a method the parameters of which to be validated when calling it using JSON-RPC protocol.

        :param maybe_method: method the parameters of which to be validated or ``None`` if called as @validate(...)
        :param kwargs: validator arguments
        """

        def decorator(method):
            method.__pjrpc_meta__ = (self, kwargs)

            return method

        # maybe_method's type depends on the usage of the decorator.  It's a function
        # if it's used as `@validate` but ``None`` if used as `@validate()`.
        if maybe_method is None:
            return decorator
        else:
            return decorator(maybe_method)

    def validate_method(self, method, params, exclude=(), **kwargs):
        """
        Validates params against method signature.

        :param method: method to validate parameters against
        :param params: parameters to be validated
        :param exclude: parameter names to be excluded from validation
        :param kwargs: additional validator arguments

        :raises :py:class:`pjrpc.server.validators.ValidationError`
        :returns: bound method parameters
        """

        signature = self.signature(method, exclude)
        return self.bind(signature, params).arguments

    def bind(self, signature, params):
        """
        Binds parameters to method.
        :param signature: method to bind parameters to
        :param params: parameters to be bound

        :raises ValidationError is parameters binding failed
        :returns: bound parameters
        """

        method_args = params if isinstance(params, (list, tuple)) else ()
        method_kwargs = params if isinstance(params, dict) else {}

        try:
            return signature.bind(*method_args, **method_kwargs)
        except TypeError as e:
            raise ValidationError([e]) from e

    @ft.lru_cache(None)
    def signature(self, method, exclude):
        """
        Returns method signature.

        :param method: method to get signature of
        :param exclude: parameters to be excluded
        :returns: signature
        """

        signature = inspect.signature(method)
        parameters = signature.parameters.copy()
        for item in exclude:
            parameters.pop(item, None)

        return signature.replace(parameters=parameters.values())
