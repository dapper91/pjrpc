import abc
import enum
import json
import pathlib
from typing import Any, Iterable, Mapping

from pjrpc.server import Method


class JSONEncoder(json.JSONEncoder):
    """
    Schema JSON encoder.
    """

    def default(self, o: Any) -> Any:
        if isinstance(o, enum.Enum):
            return o.value

        return super().default(o)


class BaseUI(abc.ABC):
    """
    Base UI.
    """

    @abc.abstractmethod
    def get_static_folder(self) -> pathlib.Path:
        """
        Returns ui statics folder.
        """

    @abc.abstractmethod
    def get_index_page(self, spec_url: str) -> str:
        """
        Returns ui index webpage.

        :param spec_url: specification url.
        """


class Specification(abc.ABC):
    """
    JSON-RPC specification.
    """

    @abc.abstractmethod
    def generate(self, root_endpoint: str, methods: Mapping[str, Iterable[Method]]) -> dict[str, Any]:
        """
        Returns specification schema.

        :param root_endpoint: root endpoint all the methods are served on
        :param methods: methods map the specification is generated for.
                        Each item is a mapping from a endpoint to methods on which the methods will be served
        """
