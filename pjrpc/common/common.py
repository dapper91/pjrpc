import json

import pjrpc


class Unset:
    """
    `Sentinel <https://en.wikipedia.org/wiki/Sentinel_value>`_ object.
    Used to distinct unset (missing) values from ``None`` ones.
    """

    def __bool__(self):
        return False

    def __repr__(self):
        return "UNSET"

    def __str__(self):
        return repr(self)


UNSET = Unset()


class JSONEncoder(json.JSONEncoder):
    """
    Library default JSON encoder. Encodes request, response and error objects to be json serializable.
    All custom encoders should be inherited from it.
    """

    def default(self, o):
        if isinstance(
            o, (pjrpc.Response, pjrpc.Request, pjrpc.BatchResponse, pjrpc.BatchRequest, pjrpc.exceptions.JsonRpcError)
        ):
            return o.to_json()

        return super().default(o)
