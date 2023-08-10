from typing import Dict, Iterable, List, Optional, Type

import docstring_parser

from pjrpc.common import UNSET, MaybeSet, exceptions
from pjrpc.common.typedefs import MethodType
from pjrpc.server.specs.extractors import BaseSchemaExtractor, Error, Example, JsonRpcError, Schema, Tag


class DocstringSchemaExtractor(BaseSchemaExtractor):
    """
    docstring method specification generator.
    """

    def extract_params_schema(self, method: MethodType, exclude: Iterable[str] = ()) -> Dict[str, Schema]:
        exclude = set(exclude)
        parameters_schema = {}

        if method.__doc__:
            doc = docstring_parser.parse(method.__doc__)
            for param in doc.params:
                if param.arg_name in exclude:
                    continue

                parameters_schema[param.arg_name] = Schema(
                    schema={'type': param.type_name},
                    required=not param.is_optional,
                    summary=param.description.split('.')[0] if param.description is not None else UNSET,
                    description=param.description if param.description is not None else UNSET,
                )

        return parameters_schema

    def extract_result_schema(self, method: MethodType) -> Schema:
        result_schema = Schema(schema={})

        if method.__doc__:
            doc = docstring_parser.parse(method.__doc__)
            if doc and doc.returns:
                result_schema = Schema(
                    schema={'type': doc.returns.type_name},
                    required=True,
                    summary=doc.returns.description.split('.')[0] if doc.returns.description is not None else UNSET,
                    description=doc.returns.description if doc.returns.description is not None else UNSET,
                )

        return result_schema

    def extract_errors_schema(
        self,
        method: MethodType,
        errors: Optional[Iterable[Type[JsonRpcError]]] = None,
    ) -> MaybeSet[List[Error]]:
        errors_schema = []

        if method.__doc__:
            error_map = {
                error.__name__: error
                for error in exceptions.JsonRpcErrorMeta.__errors_mapping__.values()
            }

            doc = docstring_parser.parse(method.__doc__)
            for error in doc.raises:
                error_cls = error_map.get(error.type_name or '')
                if error_cls:
                    errors_schema.append(
                        Error(
                            code=error_cls.code,
                            message=error_cls.message,
                        ),
                    )

        return errors_schema or UNSET

    def extract_description(self, method: MethodType) -> MaybeSet[str]:
        if method.__doc__:
            doc = docstring_parser.parse(method.__doc__)
            description = doc.long_description or UNSET
        else:
            description = UNSET

        return description

    def extract_summary(self, method: MethodType) -> MaybeSet[str]:
        if method.__doc__:
            doc = docstring_parser.parse(method.__doc__)
            description = doc.short_description or UNSET
        else:
            description = UNSET

        return description

    def extract_tags(self, method: MethodType) -> MaybeSet[List[Tag]]:
        return UNSET

    def extract_examples(self, method: MethodType) -> MaybeSet[List[Example]]:
        return UNSET

    def extract_deprecation_status(self, method: MethodType) -> MaybeSet[bool]:
        is_deprecated: MaybeSet[bool]
        if method.__doc__:
            doc = docstring_parser.parse(method.__doc__)
            is_deprecated = bool(doc.deprecation)
        else:
            is_deprecated = UNSET

        return is_deprecated
