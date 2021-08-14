import inspect
from typing import Any, Callable, Dict, Iterable, Optional

import pydantic as pd

from pjrpc.common import UNSET
from pjrpc.server.specs.extractors import BaseSchemaExtractor, Schema


class PydanticSchemaExtractor(BaseSchemaExtractor):
    """
    Pydantic method specification extractor.
    """

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
        model_schema = params_model.schema(ref_template='{model}')

        parameters_schema = {}
        for param_name, param_schema in model_schema['properties'].items():
            param_schema = self._extract_field_schema(model_schema, field_name=param_name)
            required = param_name in model_schema.get('required', [])

            parameters_schema[param_name] = Schema(
                schema=param_schema,
                summary=param_schema.get('title', UNSET),
                description=param_schema.get('description', UNSET),
                deprecated=param_schema.get('deprecated', UNSET),
                required=required,
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
        model_schema = result_model.schema(ref_template='{model}')

        result_schema = self._extract_field_schema(model_schema, field_name='result')
        required = 'result' in model_schema.get('required', [])
        if not required:
            result_schema['nullable'] = 'true'

        result_schema = Schema(
            schema=result_schema,
            summary=result_schema.get('title', UNSET),
            description=result_schema.get('description', UNSET),
            deprecated=result_schema.get('deprecated', UNSET),
            required=required,
        )

        return result_schema

    @staticmethod
    def _extract_field_schema(model_schema: Dict[str, Any], field_name: str) -> Dict[str, Any]:
        field_schema = model_schema['properties'][field_name]
        if '$ref' in field_schema:
            field_schema = model_schema['definitions'][field_schema['$ref']]

        return field_schema
