import json
from typing import Any

from . import exceptions
from .request import BatchRequest, Request
from .response import BatchResponse, Response


class JSONEncoder(json.JSONEncoder):
    """
    Library default JSON encoder. Encodes request, response and error objects to be json serializable.
    All custom encoders should be inherited from it.
    """

    def default(self, o: Any) -> Any:
        if isinstance(
            o, (
                Response, Request,
                BatchResponse, BatchRequest,
                exceptions.JsonRpcError,
            ),
        ):
            return o.to_json()

        return super().default(o)
