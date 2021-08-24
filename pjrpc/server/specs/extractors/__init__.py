import dataclasses as dc
import inspect
import itertools as it
from typing import Any, Callable, Dict, Iterable, List, Union

from pjrpc.common import UNSET, UnsetType


@dc.dataclass(frozen=True)
class Schema:
    """
    Method parameter/result schema.
    """

    schema: Dict[str, Any]
    required: bool = True
    summary: str = UNSET
    description: str = UNSET
    deprecated: bool = UNSET
    definitions: Dict[str, Any] = UNSET


@dc.dataclass(frozen=True)
class Example:
    """
    Method usage example.
    """

    params: Dict[str, Any]
    result: Any
    version: str = '2.0'
    summary: str = UNSET
    description: str = UNSET


@dc.dataclass(frozen=True)
class Tag:
    """
    A list of method tags.
    """

    name: str
    description: str = UNSET
    externalDocs: str = UNSET


@dc.dataclass(frozen=True)
class Error:
    """
    Defines an application level error.
    """

    code: int
    message: str
    data: Dict[str, Any] = UNSET


class BaseSchemaExtractor:
    """
    Base method schema extractor.
    """

    def extract_params_schema(self, method: Callable, exclude: Iterable[str] = ()) -> Dict[str, Schema]:
        """
        Extracts method parameters schema.
        """

        return {}

    def extract_result_schema(self, method: Callable) -> Schema:
        """
        Extracts method result schema.
        """

        return Schema(schema={})

    def extract_description(self, method: Callable) -> Union[UnsetType, str]:
        """
        Extracts method description.
        """

        if method.__doc__:
            doc = inspect.cleandoc(method.__doc__)
            description = '\n'.join(it.takewhile(lambda line: line, doc.split('\n')))
        else:
            description = UNSET

        return description

    def extract_summary(self, method: Callable) -> Union[UnsetType, str]:
        """
        Extracts method summary.
        """

        description = self.extract_description(method)
        if description:
            summary = description.split('.')[0]
        else:
            summary = UNSET

        return summary

    def extract_errors_schema(self, method: Callable) -> Union[UnsetType, List[Error]]:
        """
        Extracts method errors schema.
        """

        return UNSET

    def extract_tags(self, method: Callable) -> Union[UnsetType, List[Tag]]:
        """
        Extracts method tags.
        """

        return UNSET

    def extract_examples(self, method: Callable) -> Union[UnsetType, List[Example]]:
        """
        Extracts method usage examples.
        """

        return UNSET

    def extract_deprecation_status(self, method: Callable) -> Union[UnsetType, bool]:
        """
        Extracts method deprecation status.
        """

        return UNSET
