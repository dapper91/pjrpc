import functools as ft
import inspect
from typing import Any, Callable, Dict, Iterable, List, Optional

import pydantic

from pjrpc.common.typedefs import JsonRpcParams
from pjrpc.server.typedefs import ExcludeFunc

from . import base


class PydanticValidator(base.BaseValidator):
    """
    Parameters validator based on `pydantic <https://pydantic-docs.helpmanual.io/>`_ library.
    Uses python type annotations for parameters validation.

    :param coerce: if ``True`` returns converted (coerced) parameters according to parameter type annotation
                   otherwise returns parameters as is
    :param exclude_param: a function that decides if the parameters must be excluded
                          from validation (useful for dependency injection)
    """

    def __init__(self, coerce: bool = True, exclude_param: Optional[ExcludeFunc] = None, **config_args: Any):
        super().__init__(exclude_param=exclude_param)
        self._coerce = coerce

        config_args.setdefault('extra', 'forbid')

        # https://pydantic-docs.helpmanual.io/usage/model_config/
        self._model_config = pydantic.ConfigDict(**config_args)  # type: ignore[typeddict-item]

    def validate_method(
        self, method: Callable[..., Any], params: Optional['JsonRpcParams'], exclude: Iterable[str] = (), **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Validates params against method using ``pydantic`` validator.

        :param method: method to validate parameters against
        :param params: parameters to be validated
        :param exclude: parameter names to be excluded from validation

        :returns: coerced parameters if `coerce` flag is ``True`` otherwise parameters as is
        :raises: ValidationError
        """

        signature = self.signature(method, tuple(exclude))
        schema = self.build_validation_schema(signature)

        params_model = pydantic.create_model(method.__name__, **schema, model_config=self._model_config)

        bound_params = self.bind(signature, params)
        try:
            obj = params_model(**bound_params.arguments)
        except pydantic.ValidationError as e:
            raise base.ValidationError(*e.errors()) from e

        return {attr: getattr(obj, attr) for attr in obj.model_fields} if self._coerce else bound_params.arguments

    @ft.lru_cache(maxsize=None)
    def build_validation_schema(self, signature: inspect.Signature) -> Dict[str, Any]:
        """
        Builds pydantic model based validation schema from method signature.

        :param signature: method signature to build schema for
        :returns: validation schema
        """

        field_definitions = {}

        for param in signature.parameters.values():
            if param.kind is inspect.Parameter.VAR_KEYWORD:
                field_definitions[param.name] = (
                    Optional[Dict[str, param.annotation]]  # type: ignore
                    if param.annotation is not inspect.Parameter.empty else Any,
                    param.default if param.default is not inspect.Parameter.empty else None,
                )
            elif param.kind is inspect.Parameter.VAR_POSITIONAL:
                field_definitions[param.name] = (
                    Optional[List[param.annotation]]  # type: ignore
                    if param.annotation is not inspect.Parameter.empty else Any,
                    param.default if param.default is not inspect.Parameter.empty else None,
                )
            else:
                field_definitions[param.name] = (
                    param.annotation if param.annotation is not inspect.Parameter.empty else Any,
                    param.default if param.default is not inspect.Parameter.empty else ...,
                )

        return field_definitions
