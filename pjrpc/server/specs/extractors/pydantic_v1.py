import inspect
from typing import Any, Callable, Generic, Iterable, Literal, Optional, TypeVar, Union

import pydantic as pd
import pydantic.generics

from pjrpc.common import exceptions
from pjrpc.server.specs.extractors import BaseMethodInfoExtractor, ExcludeFunc

MethodType = Callable[..., Any]


def to_camel(string: str) -> str:
    return ''.join(word.capitalize() for word in string.split('_'))


MethodT = TypeVar('MethodT', bound=str)
ParamsT = TypeVar('ParamsT', bound=pd.BaseModel, covariant=True)


class JsonRpcRequest(pd.generics.GenericModel, Generic[MethodT, ParamsT]):
    class Config:
        title = "Request",
        extra = 'forbid'
        strict = True,

    jsonrpc: Literal['2.0', '1.0'] = pd.Field(title="Version", description="JSON-RPC protocol version")
    id: Optional[Union[str, int]] = pd.Field(None, description="Request identifier", examples=[1])
    method: MethodT = pd.Field(description="Method name")
    params: ParamsT = pd.Field(description="Method parameters")


ResultT = TypeVar('ResultT', covariant=True)


class JsonRpcResponseSuccess(pd.generics.GenericModel, Generic[ResultT]):
    class Config:
        title = 'Success',
        extra = 'forbid'
        strict = True,

    jsonrpc: Literal['2.0', '1.0'] = pd.Field(title="Version", description="JSON-RPC protocol version")
    id: Union[str, int] = pd.Field(description="Request identifier", examples=[1])
    result: ResultT = pd.Field(description="Method execution result")


ErrorCodeT = TypeVar('ErrorCodeT', bound=int)
ErrorDataT = TypeVar('ErrorDataT')


class JsonRpcError(pd.generics.GenericModel, Generic[ErrorCodeT, ErrorDataT]):
    class Config:
        title = "Error",
        extra = 'forbid'
        strict = True,

    code: ErrorCodeT = pd.Field(description="Error code")
    message: str = pd.Field(description="Error message")
    data: ErrorDataT = pd.Field(description="Error additional data")


JsonRpcErrorT = TypeVar('JsonRpcErrorT', bound=JsonRpcError[Any, Any], covariant=True)


class JsonRpcResponseError(pd.generics.GenericModel, Generic[JsonRpcErrorT]):
    class Config:
        title = "ResponseError",
        extra = 'forbid'
        strict = True

    jsonrpc: Literal['1.0', '2.0'] = pd.Field(title="Version", description="JSON-RPC protocol version")
    id: Union[str, int] = pd.Field(description="Request identifier", examples=[1])
    error: JsonRpcErrorT = pd.Field(description="Request error")


class PydanticMethodInfoExtractor(BaseMethodInfoExtractor):
    """
    Pydantic method specification extractor.

    :param config_args: model configuration parameters
    :param exclude: a function that decides if the parameters must be excluded
                    from schema (useful for dependency injection)
    """

    def __init__(self, exclude: Optional[ExcludeFunc] = None, **config_args: Any):
        self._exclude = exclude
        self._config_args = config_args

    def extract_params_schema(
            self,
            method_name: str,
            method: MethodType,
            ref_template: str,
    ) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
        params_model = self._build_params_model(method_name, method)
        params_schema = params_model.schema(ref_template=ref_template)

        return params_schema, params_schema.pop('definitions', {})

    def extract_request_schema(
            self,
            method_name: str,
            method: MethodType,
            ref_template: str,
    ) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
        params_model = self._build_params_model(method_name, method)

        # create inner model to set a reference to the reqeust model, not the model itself
        class RequestModel(pydantic.BaseModel):
            Config = pydantic.config.get_config(dict(self._config_args, title=f"{to_camel(method_name)}Request"))
            __root__: JsonRpcRequest[Literal[method_name], params_model]  # type: ignore[valid-type]

        request_model = pd.create_model(f'{to_camel(method.__name__)}Request', __base__=RequestModel)
        request_schema = request_model.schema(ref_template=ref_template)

        return request_schema, request_schema.pop('definitions', {})

    def extract_result_schema(
            self,
            method_name: str,
            method: MethodType,
            ref_template: str,
    ) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
        result_model = self._build_result_model(method_name, method)
        result_schema = result_model.schema(ref_template=ref_template)

        return result_schema, result_schema.pop('definitions', {})

    def extract_response_schema(
            self,
            method_name: str,
            method: MethodType,
            ref_template: str,
            errors: Optional[Iterable[type[exceptions.TypedError]]] = None,
    ) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
        return_model = self._build_result_model(method_name, method)

        error_models: list[type[pd.BaseModel]] = []
        for error in errors or []:
            class ErrorModel(pydantic.BaseModel):
                Config = pydantic.config.get_config(
                    dict(
                        self._config_args,
                        title=error.__name__,
                        json_schema_extra=dict(description=f'**{error.CODE}** {error.MESSAGE}'),
                    ),
                )
                __root__: JsonRpcResponseError[JsonRpcError[Literal[error.CODE], Any]]  # type: ignore[name-defined]

            error_models.append(pd.create_model(error.__name__, __base__=ErrorModel))

        class ResponseModel(pydantic.BaseModel):
            Config = pydantic.config.get_config(dict(title=f"{to_camel(method_name)}Response"))
            __root__: Union[(JsonRpcResponseSuccess[return_model], *error_models)]  # type: ignore[valid-type]

        response_model = pd.create_model(f'{to_camel(method.__name__)}Response', __base__=ResponseModel)
        response_schema = response_model.schema(ref_template=ref_template)
        if error_models:
            response_schema['description'] = '\n'.join(
                f'* {error.schema().get("description", error.__name__)}'
                for error in error_models
            )

        return response_schema, response_schema.pop('definitions', {})

    def extract_error_response_schema(
            self,
            method_name: str,
            method: MethodType,
            ref_template: str,
            errors: Optional[Iterable[type[exceptions.TypedError]]] = None,
    ) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
        error_models: list[type[pd.BaseModel]] = []
        for error in errors or []:
            class ErrorModel(pydantic.BaseModel):
                Config = pydantic.config.get_config(
                    dict(
                        self._config_args,
                        title=error.__name__,
                        json_schema_extra=dict(description=f'**{error.CODE}** {error.MESSAGE}'),
                    ),
                )
                __root__: JsonRpcResponseError[JsonRpcError[Literal[error.CODE], Any]]  # type: ignore[name-defined]

            error_models.append(pd.create_model(error.__name__, __base__=ErrorModel))

        class ResponseModel(pydantic.BaseModel):
            Config = pydantic.config.get_config(dict(title=f"{to_camel(method_name)}Response"))
            __root__: Union[tuple(error_models)]  # type: ignore[valid-type]

        response_model = pd.create_model(f'{to_camel(method.__name__)}Response', __base__=ResponseModel)
        response_schema = response_model.schema(ref_template=ref_template)

        if error_models:
            response_schema['description'] = '\n'.join(
                f'* {error.schema().get("description", error.__name__)}'
                for error in error_models
            )
        else:
            response_schema['description'] = 'Error'

        return response_schema, response_schema.pop('definitions', {})

    def _build_params_model(
            self,
            method_name: str,
            method: MethodType,
    ) -> type[pd.BaseModel]:
        signature = inspect.signature(method)

        field_definitions: dict[str, Any] = {}
        for idx, param in enumerate(signature.parameters.values()):
            if self._exclude and self._exclude(idx, param.name, param.annotation, param.default):
                continue

            if param.kind in [inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY]:
                field_definitions[param.name] = (
                    param.annotation if param.annotation is not inspect.Parameter.empty else Any,
                    param.default if param.default is not inspect.Parameter.empty else ...,
                )

        return pd.create_model(
            f'{to_camel(method.__name__)}Parameters',
            **field_definitions,
            __config__=pydantic.config.get_config(
                dict(self._config_args, title=f"{to_camel(method_name)}Parameters", extra='forbid'),
            ),
        )

    def _build_result_model(self, method_name: str, method: MethodType) -> type[pd.BaseModel]:
        result = inspect.signature(method)

        if result.return_annotation is inspect.Parameter.empty:
            return_annotation = Any
        elif result.return_annotation is None:
            return_annotation = None
        else:
            return_annotation = result.return_annotation

        class ResultModel(pd.BaseModel):
            Config = pydantic.config.get_config(dict(self._config_args, title=f"{to_camel(method_name)}Result"))
            __root__: return_annotation  # type: ignore[valid-type]

        return pd.create_model(f'{to_camel(method.__name__)}Result', __base__=ResultModel)
