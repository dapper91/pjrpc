import json
from typing import Any, Union

import pjrpc


class UnsetType:
    """
    `Sentinel <https://en.wikipedia.org/wiki/Sentinel_value>`_ object.
    Used to distinct unset (missing) values from ``None`` ones.
    """

    def __bool__(self) -> bool:
        return False

    def __repr__(self) -> str:
        return "UNSET"

    def __str__(self) -> str:
        return repr(self)


UNSET = UnsetType()


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


Json = Union[str, int, float, dict, bool, list, tuple, set, None]
