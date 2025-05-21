import enum
import json
from typing import Any, Literal, TypeVar, Union

from pjrpc.common import exceptions, v20


class UnsetType(enum.Enum):
    """
    `Sentinel <https://en.wikipedia.org/wiki/Sentinel_value>`_ object.
    Used to distinct unset (missing) values from ``None`` ones.
    """

    UNSET = "UNSET"

    def __bool__(self) -> Literal[False]:
        return False

    def __repr__(self) -> str:
        return "UNSET"

    def __str__(self) -> str:
        return repr(self)


UNSET = UnsetType.UNSET

MaybeSetType = TypeVar('MaybeSetType')
MaybeSet = Union[UnsetType, MaybeSetType]


class JSONEncoder(json.JSONEncoder):
    """
    Library default JSON encoder. Encodes request, response and error objects to be json serializable.
    All custom encoders should be inherited from it.
    """

    def default(self, o: Any) -> Any:
        if isinstance(
            o, (
                v20.Response, v20.Request,
                v20.BatchResponse, v20.BatchRequest,
                exceptions.JsonRpcError,
            ),
        ):
            return o.to_json()

        return super().default(o)
