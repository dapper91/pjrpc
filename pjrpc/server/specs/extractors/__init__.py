import dataclasses as dc
import inspect
import itertools as it
from typing import Any, Dict, Iterable, List, Optional, Type

from pjrpc.common import UNSET, MaybeSet, UnsetType
from pjrpc.common.exceptions import JsonRpcError
from pjrpc.common.typedefs import MethodType


@dc.dataclass(frozen=True)
class Schema:
    """
    Method parameter/result schema.
    """

    schema: Dict[str, Any]
    required: bool = True
    summary: MaybeSet[str] = UNSET
    description: MaybeSet[str] = UNSET
    deprecated: MaybeSet[bool] = UNSET
    definitions: MaybeSet[Dict[str, Any]] = UNSET


@dc.dataclass(frozen=True)
class Example:
    """
    Method usage example.
    """

    params: Dict[str, Any]
    result: Any
    version: str = '2.0'
    summary: MaybeSet[str] = UNSET
    description: MaybeSet[str] = UNSET


@dc.dataclass(frozen=True)
class ErrorExample:
    """
    Method error example.
    """

    code: int
    message: str
    data: MaybeSet[Optional[Any]] = UNSET
    summary: MaybeSet[str] = UNSET
    description: MaybeSet[str] = UNSET


@dc.dataclass(frozen=True)
class Tag:
    """
    A list of method tags.
    """

    name: str
    description: MaybeSet[str] = UNSET
    externalDocs: MaybeSet[str] = UNSET


@dc.dataclass(frozen=True)
class Error:
    """
    Defines an application level error.
    """

    code: int
    message: str
    data: MaybeSet[Dict[str, Any]] = UNSET
    data_required: MaybeSet[bool] = UNSET
    title: MaybeSet[str] = UNSET
    description: MaybeSet[str] = UNSET
    deprecated: MaybeSet[bool] = UNSET
    definitions: MaybeSet[Dict[str, Any]] = UNSET


class BaseSchemaExtractor:
    """
    Base method schema extractor.
    """

    def extract_params_schema(self, method: MethodType, exclude: Iterable[str] = ()) -> Dict[str, Schema]:
        """
        Extracts method parameters schema.
        """

        return {}

    def extract_result_schema(self, method: MethodType) -> Schema:
        """
        Extracts method result schema.
        """

        return Schema(schema={})

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

    def extract_errors_schema(
        self,
        method: MethodType,
        errors: Optional[Iterable[Type[JsonRpcError]]] = None,
    ) -> MaybeSet[List[Error]]:
        """
        Extracts method errors schema.
        """

        return UNSET

    def extract_tags(self, method: MethodType) -> MaybeSet[List[Tag]]:
        """
        Extracts method tags.
        """

        return UNSET

    def extract_examples(self, method: MethodType) -> MaybeSet[List[Example]]:
        """
        Extracts method usage examples.
        """

        return UNSET

    def extract_error_examples(
        self,
        method: MethodType,
        errors: Optional[Iterable[Type[JsonRpcError]]] = None,
    ) -> MaybeSet[List[ErrorExample]]:
        """
        Extracts method error examples.
        """

        return [
            ErrorExample(code=error.code, message=error.message, summary=error.message)
            for error in errors
        ] if errors else UNSET

    def extract_deprecation_status(self, method: MethodType) -> MaybeSet[bool]:
        """
        Extracts method deprecation status.
        """

        return UNSET
