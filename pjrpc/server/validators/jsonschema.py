from typing import Any, Dict, Iterable, Optional

import jsonschema

from pjrpc.common.typedefs import JsonRpcParams, MethodType
from pjrpc.server.typedefs import ExcludeFunc

from . import base


class JsonSchemaValidator(base.BaseValidator):
    """
    Parameters validator based on `jsonschema <https://python-jsonschema.readthedocs.io/en/stable/>`_ library.

    :param kwargs: default jsonschema validator arguments
    :param exclude_param: a function that decides if the parameters must be excluded
                          from validation (useful for dependency injection)
    """

    def __init__(self, exclude_param: Optional[ExcludeFunc] = None, **kwargs: Any):
        super().__init__(exclude_param=exclude_param)
        kwargs.setdefault('types', {'array': (list, tuple)})
        self.default_kwargs = kwargs

    def validate_method(
        self, method: MethodType, params: Optional['JsonRpcParams'], exclude: Iterable[str] = (), **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Validates params against method using ``pydantic`` validator.

        :param method: method to validate parameters against
        :param params: parameters to be validated
        :param exclude: parameter names to be excluded from validation
        :param kwargs: jsonschema validator arguments

        :raises: :py:class:`pjrpc.server.validators.ValidationError`
        """

        arguments = super().validate_method(method, params, exclude)

        try:
            kwargs = {**self.default_kwargs, **kwargs}
            jsonschema.validate(arguments, **kwargs)
        except jsonschema.ValidationError as e:
            raise base.ValidationError(str(e)) from e

        return arguments
