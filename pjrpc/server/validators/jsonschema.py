from typing import Any, Dict, Iterable, Optional

import jsonschema

from pjrpc.common.typedefs import JsonRpcParams, MethodType
from pjrpc.server.typedefs import ExcludeFunc

from . import base


class JsonSchemaValidator(base.BaseValidator):
    """
    Parameters validator factory based on `jsonschema <https://python-jsonschema.readthedocs.io/en/stable/>`_ library.

    :param kwargs: default jsonschema validator arguments
    :param exclude_param: a function that decides if the parameters must be excluded
                          from validation (useful for dependency injection)
    """

    def __init__(self, exclude_param: Optional[ExcludeFunc] = None, **kwargs: Any):
        super().__init__(exclude_param=exclude_param)
        kwargs.setdefault('types', {'array': (list, tuple)})
        self._default_kwargs = kwargs

    def build_method_validator(
            self,
            method: MethodType,
            exclude: Iterable[str] = (),
            **kwargs: Any,
    ) -> 'JsonSchemaMethodValidator':
        return JsonSchemaMethodValidator(method, self._exclude_param, exclude, **dict(self._default_kwargs, **kwargs))


class JsonSchemaMethodValidator(base.BaseMethodValidator):
    def __init__(self, method: MethodType, exclude_func: ExcludeFunc, exclude: Iterable[str] = (), **kwargs: Any):
        super().__init__(method, exclude_func, exclude)
        self._signature = self._build_signature(method, exclude_func, tuple(exclude))
        self._validator_args = kwargs

    def validate_params(self, params: Optional['JsonRpcParams']) -> Dict[str, Any]:
        """
        Validates params against method using ``pydantic`` validator.

        :param params: parameters to be validated

        :raises: :py:class:`pjrpc.server.validators.ValidationError`
        """

        arguments = super().validate_params(params)

        try:
            jsonschema.validate(arguments, **self._validator_args)
        except jsonschema.ValidationError as e:
            raise base.ValidationError(str(e)) from e

        return arguments
