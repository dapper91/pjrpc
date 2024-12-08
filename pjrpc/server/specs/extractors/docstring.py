from typing import Any, Dict, Iterable, List, Optional, Tuple, Type

import docstring_parser

from pjrpc.common import UNSET, MaybeSet, exceptions
from pjrpc.common.typedefs import MethodType
from pjrpc.server.specs.extractors import BaseSchemaExtractor, JsonRpcError
from pjrpc.server.specs.schemas import build_request_schema, build_response_schema
from pjrpc.server.typedefs import ExcludeFunc


class DocstringSchemaExtractor(BaseSchemaExtractor):
    """
    docstring method specification generator.

    :param exclude_param: a function that decides if the parameters must be excluded
                          from schema (useful for dependency injection)
    """

    def __init__(self, exclude_param: Optional[ExcludeFunc] = None):
        self._exclude_param = exclude_param or (lambda *args: False)

    def extract_params_schema(
            self,
            method_name: str,
            method: MethodType,
            ref_template: str,
            exclude: Iterable[str] = (),
    ) -> Tuple[Dict[str, Any], Dict[str, Dict[str, Any]]]:
        exclude = set(exclude)
        parameters_schema = {}

        if method.__doc__:
            doc = docstring_parser.parse(method.__doc__)
            for param in doc.params:
                if param.arg_name in exclude or self._exclude_param(param.arg_name, None, None):
                    continue

                parameters_schema[param.arg_name] = {
                    'title': param.arg_name.capitalize(),
                    'description': param.description if param.description is not None else UNSET,
                    'type': param.type_name,
                }

        return parameters_schema, {}

    def extract_request_schema(
            self,
            method_name: str,
            method: MethodType,
            ref_template: str,
            exclude: Iterable[str] = (),
    ) -> Tuple[Dict[str, Any], Dict[str, Dict[str, Any]]]:
        exclude = set(exclude)
        parameters_schema, components = self.extract_params_schema(method_name, method, ref_template, exclude)

        return build_request_schema(method_name, parameters_schema), components

    def extract_result_schema(
            self,
            method_name: str,
            method: MethodType,
            ref_template: str,
    ) -> Tuple[Dict[str, Any], Dict[str, Dict[str, Any]]]:
        result_schema = {}

        if method.__doc__:
            doc = docstring_parser.parse(method.__doc__)
            if doc and doc.returns:
                result_schema = {
                    'type': doc.returns.type_name,
                    'title': 'Result',
                    'description': doc.returns.description if doc.returns.description is not None else UNSET,
                }

        return result_schema, {}

    def extract_response_schema(
            self,
            method_name: str,
            method: MethodType,
            ref_template: str,
            errors: Optional[Iterable[Type[JsonRpcError]]] = None,
    ) -> Tuple[Dict[str, Any], Dict[str, Dict[str, Any]]]:
        result_schema, components = self.extract_result_schema(method_name, method, ref_template)

        return build_response_schema(result_schema, errors or []), components

    def extract_errors(self, method: MethodType) -> MaybeSet[List[Type[JsonRpcError]]]:
        errors_schema: List[Type[JsonRpcError]] = []

        if method.__doc__:
            error_map = {
                error.__name__: error
                for error in exceptions.JsonRpcErrorMeta.__errors_mapping__.values()
            }

            doc = docstring_parser.parse(method.__doc__)
            for error in doc.raises:
                error_cls = error_map.get(error.type_name or '')
                if error_cls:
                    errors_schema.append(error_cls)

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

    def extract_deprecation_status(self, method: MethodType) -> MaybeSet[bool]:
        is_deprecated: MaybeSet[bool]
        if method.__doc__:
            doc = docstring_parser.parse(method.__doc__)
            is_deprecated = bool(doc.deprecation)
        else:
            is_deprecated = UNSET

        return is_deprecated
