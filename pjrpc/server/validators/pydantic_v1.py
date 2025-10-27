import inspect
from typing import Any, Optional

import pydantic

from pjrpc.common.typedefs import JsonRpcParamsT
from pjrpc.server.dispatcher import Method

from . import base
from .base import ExcludeFunc, MethodType


class PydanticValidatorFactory(base.BaseValidatorFactory):
    """
    Method parameters validator factory based on `pydantic <https://pydantic-docs.helpmanual.io/>`_ library.
    Uses python type annotations for parameters validation.

    :param exclude: a function that decides if the parameters must be excluded
                    from validation (useful for dependency injection)
    """

    def __init__(self, exclude: Optional[ExcludeFunc] = None, **config_args: Any):
        super().__init__(exclude=exclude)

        config_args.setdefault('extra', 'forbid')
        self._model_config = config_args

    def __call__(self, method: Method) -> Method:
        self.build(method.func)
        return method

    def build(self, method: MethodType) -> 'PydanticValidator':
        return PydanticValidator(method, self._model_config, self._exclude)


class PydanticValidator(base.BaseValidator):
    """
    Pydantic method parameters validator based on `pydantic <https://docs.pydantic.dev/latest/>`_ library.
    """

    def __init__(
        self,
        method: MethodType,
        model_config: dict[str, Any],
        exclude: Optional[ExcludeFunc] = None,
    ):
        super().__init__(method, exclude)
        self._model_config = model_config
        self._params_model = self._build_validation_model(method.__name__)

    def validate_params(self, params: Optional['JsonRpcParamsT']) -> dict[str, Any]:
        """
        Validates params against method using ``pydantic`` validator.

        :param params: parameters to be validated
        """

        model_fields: tuple[str, ...] = tuple(self._params_model.__fields__)  # type: ignore[arg-type]

        if isinstance(params, dict):
            params_dict = params
        elif isinstance(params, (list, tuple)):
            if len(params) > len(fields := list(model_fields)):
                fields.extend((f'params.{n}' for n in range(len(fields), len(params) + 1)))
            params_dict = {name: value for name, value in zip(fields, params)}
        else:
            raise AssertionError("unreachable")

        try:
            obj = self._params_model.parse_obj(params_dict)
        except pydantic.ValidationError as e:
            raise base.ValidationError(*e.errors()) from e

        return {field_name: obj.__dict__[field_name] for field_name in model_fields}

    def _build_validation_model(self, method_name: str) -> type[pydantic.BaseModel]:
        schema = self._build_validation_schema(self._signature)
        return pydantic.create_model(method_name, **schema, __config__=pydantic.config.get_config(self._model_config))

    def _build_validation_schema(self, signature: inspect.Signature) -> dict[str, Any]:
        """
        Builds pydantic model based validation schema from method signature.

        :param signature: method signature to build schema for
        :returns: validation schema
        """

        field_definitions: dict[str, tuple[Any, Any]] = {}

        for param in signature.parameters.values():
            if param.kind is inspect.Parameter.VAR_KEYWORD:
                field_definitions[param.name] = (
                    Optional[dict[str, param.annotation]]  # type: ignore
                    if param.annotation is not inspect.Parameter.empty else Any,
                    param.default if param.default is not inspect.Parameter.empty else None,
                )
            elif param.kind is inspect.Parameter.VAR_POSITIONAL:
                field_definitions[param.name] = (
                    Optional[dict[param.annotation]]  # type: ignore
                    if param.annotation is not inspect.Parameter.empty else Any,
                    param.default if param.default is not inspect.Parameter.empty else None,
                )
            else:
                field_definitions[param.name] = (
                    param.annotation if param.annotation is not inspect.Parameter.empty else Any,
                    param.default if param.default is not inspect.Parameter.empty else ...,
                )

        return field_definitions
