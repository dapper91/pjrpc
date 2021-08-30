import abc
import enum
import json
from typing import Any, Dict, Iterable, Optional

from pjrpc.server import Method


class JSONEncoder(json.JSONEncoder):
    """
    Schema JSON encoder.
    """

    def default(self, o: Any) -> Any:
        if isinstance(o, enum.Enum):
            return o.value

        return super().default(o)


class BaseUI:
    """
    Base UI.
    """

    def get_static_folder(self) -> str:
        """
        Returns ui statics folder.
        """

    def get_index_page(self, spec_url: str) -> str:
        """
        Returns ui index webpage.

        :param spec_url: specification url.
        """


class Specification(abc.ABC):
    """
    JSON-RPC specification.

    :param path: specification url path suffix
    :param ui: specification ui instance
    :param ui_path: specification ui url path suffix
    """

    def __init__(self, path: str = '/spec.json', ui: Optional[BaseUI] = None, ui_path: Optional[str] = None):
        self._path = path
        self._ui = ui
        self._ui_path = ui_path

    @property
    def path(self) -> str:
        """
        Returns specification url path.
        """

        return self._path

    @property
    def ui(self) -> Optional[BaseUI]:
        """
        Returns ui instance.
        """

        return self._ui

    @property
    def ui_path(self) -> Optional[str]:
        """
        Returns specification ui url path.
        """

        return self._ui_path

    @abc.abstractmethod
    def schema(self, path: str, methods: Iterable[Method] = (), methods_map: Dict[str, Iterable[Method]] = {}) -> dict:
        """
        Returns specification schema.

        :param path: methods endpoint path
        :param methods: methods list the specification is generated for
        :param methods_map: methods map the specification is generated for.
                            Each item is a mapping from a prefix to methods on which the methods will be served
        """
