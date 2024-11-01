import inspect
import itertools as it
from typing import Any, Dict, Iterable, List, Optional, Tuple, Type

from pjrpc.common import UNSET, MaybeSet, UnsetType
from pjrpc.common.exceptions import JsonRpcError
from pjrpc.common.typedefs import MethodType


class BaseSchemaExtractor:
    """
    Base method schema extractor.
    """

    def extract_params_schema(
            self,
            method_name: str,
            method: MethodType,
            ref_template: str,
            exclude: Iterable[str] = (),
    ) -> Tuple[Dict[str, Any], Dict[str, Dict[str, Any]]]:
        """
        Extracts params schema.
        """

        return {}, {}

    def extract_request_schema(
            self,
            method_name: str,
            method: MethodType,
            ref_template: str,
            exclude: Iterable[str] = (),
    ) -> Tuple[Dict[str, Any], Dict[str, Dict[str, Any]]]:
        """
        Extracts request schema.
        """

        return {}, {}

    def extract_result_schema(
            self,
            method_name: str,
            method: MethodType,
            ref_template: str,
    ) -> Tuple[Dict[str, Any], Dict[str, Dict[str, Any]]]:
        """
        Extracts result schema.
        """

        return {}, {}

    def extract_response_schema(
            self,
            method_name: str,
            method: MethodType,
            ref_template: str,
            errors: Optional[Iterable[Type[JsonRpcError]]] = None,
    ) -> Tuple[Dict[str, Any], Dict[str, Dict[str, Any]]]:
        """
        Extracts response schema.
        """

        return {}, {}

    def extract_error_response_schema(
            self,
            method_name: str,
            method: MethodType,
            ref_template: str,
            errors: Optional[Iterable[Type[JsonRpcError]]] = None,
    ) -> Tuple[Dict[str, Any], Dict[str, Dict[str, Any]]]:
        """
        Extracts error response schema.
        """

        return {}, {}

    def extract_description(self, method: MethodType) -> MaybeSet[str]:
        """
        Extracts method description.
        """

        description: MaybeSet[str]
        if method.__doc__:
            doc = inspect.cleandoc(method.__doc__)
            description = '\n'.join(it.takewhile(lambda line: line, doc.split('\n')))
        else:
            description = UNSET

        return description

    def extract_summary(self, method: MethodType) -> MaybeSet[str]:
        """
        Extracts method summary.
        """

        description = self.extract_description(method)

        summary: MaybeSet[str]
        if not isinstance(description, UnsetType):
            summary = description.split('.')[0]
        else:
            summary = UNSET

        return summary

    def extract_errors(self, method: MethodType) -> MaybeSet[List[Type[JsonRpcError]]]:
        """
        Extracts method errors.
        """

        return UNSET

    def extract_deprecation_status(self, method: MethodType) -> MaybeSet[bool]:
        """
        Extracts method deprecation status.
        """

        return UNSET
