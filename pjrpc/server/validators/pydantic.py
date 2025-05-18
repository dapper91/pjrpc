import inspect
from typing import Any, Dict, Iterable, List, Optional, Type

import pydantic

from pjrpc.common.typedefs import JsonRpcParams, MethodType
from pjrpc.server.typedefs import ExcludeFunc

from . import base


class PydanticValidator(base.BaseValidator):
    """
    Method parameters validator factory based on `pydantic <https://pydantic-docs.helpmanual.io/>`_ library.
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

    def build_method_validator(
            self,
            method: MethodType,
            exclude: Iterable[str] = (),
            **kwargs: Any,
    ) -> 'PydanticMethodValidator':
        return PydanticMethodValidator(method, self._exclude_param, exclude, self._coerce, self._model_config)


class PydanticMethodValidator(base.BaseMethodValidator):
    """
    Pydantic method parameters validator based on `pydantic <https://pydantic-docs.helpmanual.io/>`_ library.
    """

    def __init__(
            self,
            method: MethodType,
            exclude_func: ExcludeFunc,
            exclude: Iterable[str],
            coerce: bool,
            model_config: pydantic.ConfigDict,
    ):
        super().__init__(method, exclude_func, exclude)
        self._coerce = coerce
        self._model_config = model_config
        self._params_model = self._build_validation_model(method.__name__)

    def validate_params(self, params: Optional['JsonRpcParams']) -> Dict[str, Any]:
        """
        Validates params against method using ``pydantic`` validator.

        :param params: parameters to be validated

        :returns: coerced parameters if `coerce` flag is ``True`` otherwise parameters as is
        :raises: ValidationError
        """

        bound_params = self._bind(params)
        try:
            obj = self._params_model(**bound_params.arguments)
        except pydantic.ValidationError as e:
            raise base.ValidationError(*e.errors()) from e

        return {attr: getattr(obj, attr) for attr in obj.model_fields} if self._coerce else bound_params.arguments

    def _build_validation_model(self, method_name: str) -> Type[pydantic.BaseModel]:
        schema = self._build_validation_schema(self._signature)
        return pydantic.create_model(method_name, **schema, __config__=self._model_config)

    def _build_validation_schema(self, signature: inspect.Signature) -> Dict[str, Any]:
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
