import inspect
from typing import Any, Callable, Dict, Iterable, List, Optional, Type, Union

import pydantic as pd

from pjrpc.common import UNSET, UnsetType
from pjrpc.common.exceptions import JsonRpcError
from pjrpc.server.specs.extractors import BaseSchemaExtractor, Error, Schema


class PydanticSchemaExtractor(BaseSchemaExtractor):
    """
    Pydantic method specification extractor.
    """

    def __init__(self, ref_template: str = '#/components/schemas/{model}'):
        self._ref_template = ref_template

    def extract_params_schema(self, method: Callable, exclude: Iterable[str] = ()) -> Dict[str, Schema]:
        exclude = set(exclude)
        signature = inspect.signature(method)

        field_definitions = {}
        for param in signature.parameters.values():
            if param.name in exclude:
                continue

            if param.kind in [inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY]:
                field_definitions[param.name] = (
                    param.annotation if param.annotation is not inspect.Parameter.empty else Any,
                    param.default if param.default is not inspect.Parameter.empty else ...,
                )

        params_model = pd.create_model('RequestModel', **field_definitions)
        model_schema = params_model.schema(ref_template=self._ref_template)

        parameters_schema = {}
        for param_name, param_schema in model_schema['properties'].items():
            required = param_name in model_schema.get('required', [])

            parameters_schema[param_name] = Schema(
                schema=param_schema,
                summary=param_schema.get('title', UNSET),
                description=param_schema.get('description', UNSET),
                deprecated=param_schema.get('deprecated', UNSET),
                required=required,
                definitions=model_schema.get('definitions'),
            )

        return parameters_schema

    def extract_result_schema(self, method: Callable) -> Schema:
        result = inspect.signature(method)

        if result.return_annotation is inspect.Parameter.empty:
            return_annotation = Any
        elif result.return_annotation is None:
            return_annotation = Optional[None]
        else:
            return_annotation = result.return_annotation

        result_model = pd.create_model('ResultModel', result=(return_annotation, pd.fields.Undefined))
        model_schema = result_model.schema(ref_template=self._ref_template)

        result_schema = model_schema['properties']['result']
        required = 'result' in model_schema.get('required', [])
        if not required:
            result_schema['nullable'] = 'true'

        result_schema = Schema(
            schema=result_schema,
            summary=result_schema.get('title', UNSET),
            description=result_schema.get('description', UNSET),
            deprecated=result_schema.get('deprecated', UNSET),
            required=required,
            definitions=model_schema.get('definitions'),
        )

        return result_schema

    def extract_errors_schema(
        self,
        method: Callable,
        errors: Optional[Iterable[JsonRpcError]] = None,
    ) -> Union[UnsetType, List[Error]]:
        if errors:
            errors_schema = []
            for error in errors:
                field_definitions = {}
                for field_name, annotation in self._get_annotations(error).items():
                    if field_name.startswith('_'):
                        continue

                    field_definitions[field_name] = (annotation, getattr(error, field_name, ...))

                result_model = pd.create_model(error.message, **field_definitions)
                model_schema = result_model.schema(ref_template=self._ref_template)

                data_schema = model_schema['properties'].get('data', UNSET)
                required = 'data' in model_schema.get('required', [])

                errors_schema.append(
                    Error(
                        code=error.code,
                        message=error.message,
                        data=data_schema,
                        data_required=required,
                        title=error.message,
                        description=inspect.cleandoc(error.__doc__) if error.__doc__ is not None else UNSET,
                        deprecated=model_schema.get('deprecated', UNSET),
                        definitions=model_schema.get('definitions'),
                    ),
                )
            return errors_schema

        else:
            return UNSET

    @staticmethod
    def _extract_field_schema(model_schema: Dict[str, Any], field_name: str) -> Dict[str, Any]:
        field_schema = model_schema['properties'][field_name]
        if '$ref' in field_schema:
            field_schema = model_schema['definitions'][field_schema['$ref']]

        return field_schema

    @staticmethod
    def _get_annotations(cls: Type):
        annotations = {}
        for patent in cls.mro():
            annotations.update(**getattr(patent, '__annotations__', {}))

        return annotations
