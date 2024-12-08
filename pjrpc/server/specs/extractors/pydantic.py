import inspect
from typing import Any, Dict, Generic, Iterable, Literal, Optional, Tuple, Type, TypeVar, Union

import pydantic as pd

from pjrpc.common import exceptions
from pjrpc.common.typedefs import MethodType
from pjrpc.server.specs.extractors import BaseSchemaExtractor
from pjrpc.server.typedefs import ExcludeFunc


def to_camel(string: str) -> str:
    return ''.join(word.capitalize() for word in string.split('_'))


MethodT = TypeVar('MethodT', bound=str)
ParamsT = TypeVar('ParamsT', bound=pd.BaseModel, covariant=True)


class JsonRpcRequest(
    pd.BaseModel, Generic[MethodT, ParamsT],
    title="Request",
    extra='forbid', strict=True,
):
    jsonrpc: Literal['2.0', '1.0'] = pd.Field(title="Version", description="JSON-RPC protocol version")
    id: Optional[Union[str, int]] = pd.Field(None, description="Request identifier", examples=[1])
    method: MethodT = pd.Field(description="Method name")
    params: ParamsT = pd.Field(description="Method parameters")


RequestT = TypeVar('RequestT', bound=Union[JsonRpcRequest[Any, Any]])


class JsonRpcRequestWrapper(pd.RootModel[RequestT], Generic[RequestT], title="Request"):
    pass


ResultT = TypeVar('ResultT', covariant=True)


class JsonRpcResponseSuccess(
    pd.BaseModel, Generic[ResultT],
    title='Success',
    extra='forbid', strict=True,
):
    jsonrpc: Literal['2.0', '1.0'] = pd.Field(title="Version", description="JSON-RPC protocol version")
    id: Union[str, int] = pd.Field(description="Request identifier", examples=[1])
    result: ResultT = pd.Field(description="Method execution result")


ErrorCodeT = TypeVar('ErrorCodeT', bound=int)
ErrorDataT = TypeVar('ErrorDataT')


class JsonRpcError(
    pd.BaseModel, Generic[ErrorCodeT, ErrorDataT],
    title="Error",
    extra='forbid', strict=True,
):
    code: ErrorCodeT = pd.Field(description="Error code")
    message: str = pd.Field(description="Error message")
    data: ErrorDataT = pd.Field(description="Error additional data")


JsonRpcErrorT = TypeVar('JsonRpcErrorT', bound=JsonRpcError[Any, Any], covariant=True)


class JsonRpcResponseError(
    pd.BaseModel, Generic[JsonRpcErrorT],
    title="ResponseError",
    extra='forbid', strict=True,
):
    jsonrpc: Literal['1.0', '2.0'] = pd.Field(title="Version", description="JSON-RPC protocol version")
    id: Union[str, int] = pd.Field(description="Request identifier", examples=[1])
    error: JsonRpcErrorT = pd.Field(description="Request error")


ResponseT = TypeVar('ResponseT', bound=Union[JsonRpcResponseSuccess[Any], JsonRpcResponseError[Any]])


class JsonRpcResponseWrapper(pd.RootModel[ResponseT], Generic[ResponseT], title="Response"):
    pass


class PydanticSchemaExtractor(BaseSchemaExtractor):
    """
    Pydantic method specification extractor.

    :param config_args: model configuration parameters
    :param exclude_param: a function that decides if the parameters must be excluded
                          from schema (useful for dependency injection)
    """

    def __init__(self, exclude_param: Optional[ExcludeFunc] = None, **config_args: Any):
        self._exclude_param = exclude_param or (lambda *args: False)
        self._config_args = config_args

    def extract_params_schema(
            self,
            method_name: str,
            method: MethodType,
            ref_template: str,
            exclude: Iterable[str] = (),
    ) -> Tuple[Dict[str, Any], Dict[str, Dict[str, Any]]]:
        params_model = self._build_params_model(method_name, method, exclude)
        params_schema = params_model.model_json_schema(ref_template=ref_template)

        return params_schema, params_schema.pop('$defs', {})

    def extract_request_schema(
            self,
            method_name: str,
            method: MethodType,
            ref_template: str,
            exclude: Iterable[str] = (),
    ) -> Tuple[Dict[str, Any], Dict[str, Dict[str, Any]]]:
        exclude = set(exclude)

        params_model = self._build_params_model(method_name, method, exclude)
        request_model = pd.create_model(
            f'{to_camel(method_name)}Request',
            __base__=JsonRpcRequestWrapper[
                JsonRpcRequest[Literal[method_name], params_model],  # type: ignore[valid-type]
            ],
            __cls_kwargs__=self._config_args,
        )
        request_schema = request_model.model_json_schema(ref_template=ref_template)

        return request_schema, request_schema.pop('$defs', {})

    def extract_result_schema(
            self,
            method_name: str,
            method: MethodType,
            ref_template: str,
    ) -> Tuple[Dict[str, Any], Dict[str, Dict[str, Any]]]:
        result_model = self._build_result_model(method_name, method)
        result_schema = result_model.model_json_schema(ref_template=ref_template)

        return result_schema, result_schema.pop('$defs', {})

    def extract_response_schema(
            self,
            method_name: str,
            method: MethodType,
            ref_template: str,
            errors: Optional[Iterable[Type[exceptions.JsonRpcError]]] = None,
    ) -> Tuple[Dict[str, Any], Dict[str, Dict[str, Any]]]:
        return_model = self._build_result_model(method_name, method)

        response_model: Type[pd.BaseModel]
        error_models = tuple(
            pd.create_model(
                error.__name__,
                __base__=JsonRpcResponseError[JsonRpcError[Literal[error.code], Any]],  # type: ignore[name-defined]
                __cls_kwargs__=dict(
                    self._config_args,
                    title=error.__name__,
                    json_schema_extra=dict(description=f'**{error.code}** {error.message}'),
                ),
            ) for error in errors or []
        )

        response_model = pd.create_model(
            f'{to_camel(method_name)}Response',
            __base__=JsonRpcResponseWrapper[
                Union[(JsonRpcResponseSuccess[return_model], *error_models)],  # type: ignore[valid-type]
            ],
        )
        response_schema = response_model.model_json_schema(ref_template=ref_template)
        if error_models:
            response_schema['description'] = '\n'.join(
                f'* {error.model_json_schema().get("description", error.__name__)}'
                for error in error_models
            )

        return response_schema, response_schema.pop('$defs', {})

    def extract_error_response_schema(
            self,
            method_name: str,
            method: MethodType,
            ref_template: str,
            errors: Optional[Iterable[Type[exceptions.JsonRpcError]]] = None,
    ) -> Tuple[Dict[str, Any], Dict[str, Dict[str, Any]]]:
        error_models = tuple(
            pd.create_model(
                error.__name__,
                __base__=JsonRpcResponseError[JsonRpcError[Literal[error.code], Any]],  # type: ignore[name-defined]
                __cls_kwargs__=dict(
                    self._config_args,
                    title=error.__name__,
                    json_schema_extra=dict(description=f'**{error.code}** {error.message}'),
                ),
            ) for error in errors or []
        )
        if len(error_models) == 1:
            response_model = pd.create_model(
                f'{to_camel(method_name)}Response',
                __base__=JsonRpcResponseWrapper[Union[error_models]],  # type: ignore[valid-type]
            )
            response_schema = response_model.model_json_schema(ref_template=ref_template)
        else:
            response_model = pd.create_model(
                f'{to_camel(method_name)}Response',
                __base__=JsonRpcResponseWrapper[Union[error_models]],  # type: ignore[valid-type]
            )
            response_schema = response_model.model_json_schema(ref_template=ref_template)

        if error_models:
            response_schema['description'] = '\n'.join(
                f'* {error.model_json_schema().get("description", error.__name__)}'
                for error in error_models
            )
        else:
            response_schema['description'] = 'Error'

        return response_schema, response_schema.pop('$defs', {})

    def _build_params_model(
            self,
            method_name: str,
            method: MethodType,
            exclude: Iterable[str] = (),
    ) -> Type[pd.BaseModel]:
        signature = inspect.signature(method)

        field_definitions: Dict[str, Any] = {}
        for param in signature.parameters.values():
            if param.name in exclude or self._exclude_param(param.name, param.annotation, param.default):
                continue

            if param.kind in [inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY]:
                field_definitions[param.name] = (
                    param.annotation if param.annotation is not inspect.Parameter.empty else Any,
                    param.default if param.default is not inspect.Parameter.empty else ...,
                )

        return pd.create_model(
            f'{to_camel(method_name)}Parameters',
            **field_definitions,
            __cls_kwargs__=dict(self._config_args, extra='forbid'),
        )

    def _build_result_model(self, method_name: str, method: MethodType) -> Type[pd.BaseModel]:
        result = inspect.signature(method)

        if result.return_annotation is inspect.Parameter.empty:
            return_annotation = Any
        elif result.return_annotation is None:
            return_annotation = Optional[None]
        else:
            return_annotation = result.return_annotation

        return pd.create_model(
            f'{to_camel(method_name)}Result',
            __base__=pd.RootModel[return_annotation],  # type: ignore[valid-type]
            __cls_kwargs__=dict(self._config_args),
        )
