import json
from typing import Any, Dict, Literal, TypeVar, Union

import pjrpc
from pjrpc.common.typedefs import Json  # noqa: for back compatibility


class UnsetType:
    """
    `Sentinel <https://en.wikipedia.org/wiki/Sentinel_value>`_ object.
    Used to distinct unset (missing) values from ``None`` ones.
    """

    def __bool__(self) -> Literal[False]:
        return False

    def __repr__(self) -> str:
        return "UNSET"

    def __str__(self) -> str:
        return repr(self)

    def __copy__(self) -> 'UnsetType':
        return self

    def __deepcopy__(self, memo: Dict[str, Any]) -> 'UnsetType':
        return self


UNSET: UnsetType = UnsetType()

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
                pjrpc.Response, pjrpc.Request,
                pjrpc.BatchResponse, pjrpc.BatchRequest,
                pjrpc.exceptions.JsonRpcError,
            ),
        ):
            return o.to_json()

        return super().default(o)
