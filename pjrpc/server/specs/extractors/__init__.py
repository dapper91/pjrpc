import dataclasses as dc
import inspect
import itertools as it
from typing import Any, Dict, Iterable, List, Optional, Type, Union

from pjrpc.common import UNSET, UnsetType
from pjrpc.common.exceptions import JsonRpcError
from pjrpc.common.typedefs import MethodType


@dc.dataclass(frozen=True)
class Schema:
    """
    Method parameter/result schema.
    """

    schema: Dict[str, Any]
    required: bool = True
    summary: Union[str, UnsetType] = UNSET
    description: Union[str, UnsetType] = UNSET
    deprecated: Union[bool, UnsetType] = UNSET
    definitions: Union[Dict[str, Any], UnsetType] = UNSET


@dc.dataclass(frozen=True)
class Example:
    """
    Method usage example.
    """

    params: Dict[str, Any]
    result: Any
    version: str = '2.0'
    summary: Union[str, UnsetType] = UNSET
    description: Union[str, UnsetType] = UNSET


@dc.dataclass(frozen=True)
class ErrorExample:
    """
    Method error example.
    """

    code: int
    message: str
    data: Union[Optional[Any], UnsetType] = UNSET
    summary: Union[str, UnsetType] = UNSET
    description: Union[str, UnsetType] = UNSET


@dc.dataclass(frozen=True)
class Tag:
    """
    A list of method tags.
    """

    name: str
    description: Union[str, UnsetType] = UNSET
    externalDocs: Union[str, UnsetType] = UNSET


@dc.dataclass(frozen=True)
class Error:
    """
    Defines an application level error.
    """

    code: int
    message: str
    data: Union[Dict[str, Any], UnsetType] = UNSET
    data_required: Union[bool, UnsetType] = UNSET
    title: Union[str, UnsetType] = UNSET
    description: Union[str, UnsetType] = UNSET
    deprecated: Union[bool, UnsetType] = UNSET
    definitions: Union[Dict[str, Any], UnsetType] = UNSET


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

    def extract_description(self, method: MethodType) -> Union[UnsetType, str]:
        """
        Extracts method description.
        """

        description: Union[UnsetType, str]
        if method.__doc__:
            doc = inspect.cleandoc(method.__doc__)
            description = '\n'.join(it.takewhile(lambda line: line, doc.split('\n')))
        else:
            description = UNSET

        return description

    def extract_summary(self, method: MethodType) -> Union[UnsetType, str]:
        """
        Extracts method summary.
        """

        description = self.extract_description(method)

        summary: Union[UnsetType, str]
        if not isinstance(description, UnsetType):
            summary = description.split('.')[0]
        else:
            summary = UNSET

        return summary

    def extract_errors_schema(
        self,
        method: MethodType,
        errors: Optional[Iterable[Type[JsonRpcError]]] = None,
    ) -> Union[UnsetType, List[Error]]:
        """
        Extracts method errors schema.
        """

        return UNSET

    def extract_tags(self, method: MethodType) -> Union[UnsetType, List[Tag]]:
        """
        Extracts method tags.
        """

        return UNSET

    def extract_examples(self, method: MethodType) -> Union[UnsetType, List[Example]]:
        """
        Extracts method usage examples.
        """

        return UNSET

    def extract_error_examples(
        self,
        method: MethodType,
        errors: Optional[Iterable[Type[JsonRpcError]]] = None,
    ) -> Union[UnsetType, List[ErrorExample]]:
        """
        Extracts method error examples.
        """

        return [
            ErrorExample(code=error.code, message=error.message, summary=error.message)
            for error in errors
        ] if errors else UNSET

    def extract_deprecation_status(self, method: MethodType) -> Union[UnsetType, bool]:
        """
        Extracts method deprecation status.
        """

        return UNSET
