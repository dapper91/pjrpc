import functools as ft
import inspect
from typing import List, Dict, Optional

import pydantic

from . import base


class PydanticValidator(base.BaseValidator):
    """
    Parameters validator based on `pydantic <https://pydantic-docs.helpmanual.io/>`_ library.
    Uses python type annotations for parameters validation.

    :param coerce: if ``True`` returns converted (coerced) parameters according to parameter type annotation
                   otherwise returns parameters as is
    """

    def __init__(self, coerce=True, **config_args):
        self._coerce = coerce

        config_args.setdefault('extra', 'forbid')

        # https://pydantic-docs.helpmanual.io/usage/model_config/
        self._model_config = type('ModelConfig', (pydantic.BaseConfig,), config_args)

    def validate_method(self, method, params, exclude=(), **kwargs):
        """
        Validates params against method using ``pydantic`` validator.

        :param method: method to validate parameters against
        :param params: parameters to be validated
        :param exclude: parameter names to be excluded from validation

        :returns: coerced parameters if `coerce` flag is ``True`` otherwise parameters as is
        :raises: ValidationError
        """

        signature = self.signature(method, exclude)
        schema = self.build_validation_schema(signature)

        params_model = pydantic.create_model(method.__name__, **schema, __config__=self._model_config)

        bound_params = self.bind(signature, params)
        try:
            obj = params_model(**bound_params.arguments)
        except pydantic.ValidationError as e:
            raise base.ValidationError(e.errors()) from e

        return {attr: getattr(obj, attr) for attr in obj.__fields_set__} if self._coerce else bound_params.arguments

    @ft.lru_cache(maxsize=None)
    def build_validation_schema(self, signature):
        """
        Builds pydantic model based validation schema from method signature.

        :param signature: method signature to build schema for
        :returns: validation schema
        """

        field_definitions = {}

        for param in signature.parameters.values():
            if param.kind is inspect.Parameter.VAR_KEYWORD:
                field_definitions[param.name] = (
                    Optional[Dict[str, param.annotation]] if param.annotation is not inspect.Parameter.empty else ...,
                    param.default if param.default is not inspect.Parameter.empty else ...,
                )
            elif param.kind is inspect.Parameter.VAR_POSITIONAL:
                field_definitions[param.name] = (
                    Optional[List[param.annotation]] if param.annotation is not inspect.Parameter.empty else ...,
                    param.default if param.default is not inspect.Parameter.empty else ...,
                )
            else:
                field_definitions[param.name] = (
                    param.annotation if param.annotation is not inspect.Parameter.empty else ...,
                    param.default if param.default is not inspect.Parameter.empty else ...,
                )

        return field_definitions
