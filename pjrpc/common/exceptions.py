"""
Definition of package exceptions and JSON-RPC protocol errors.
"""

import dataclasses as dc
from typing import Any, ClassVar, Optional

from .common import UNSET, MaybeSet

JsonT = Any


class BaseError(Exception):
    """
    Base package error. All package errors are inherited from it.
    """


class ProtocolError(BaseError):
    """
    Raised when JSON-RPC protocol is violated.
    """


class IdentityError(ProtocolError):
    """
    Raised when a batch requests/responses identifiers are not unique or missing.
    """


class DeserializationError(ProtocolError, ValueError):
    """
    Request/response deserializatoin error.
    Raised when request/response json has incorrect format.
    """


@dc.dataclass
class JsonRpcError(BaseError):
    """
    `JSON-RPC <https://www.jsonrpc.org>`_ protocol error.
    For more information see `Error object <https://www.jsonrpc.org/specification#error_object>`_.
    All JSON-RPC protocol errors are inherited from it.

    :param code: number that indicates the error type
    :param message: short description of the error
    :param data: value that contains additional information about the error. May be omitted.
    """

    code: int
    message: str
    data: MaybeSet[JsonT] = dc.field(repr=False, default=UNSET)

    @classmethod
    def get_typed_error_by_code(cls, code: int, message: str, data: MaybeSet[JsonT]) -> Optional['JsonRpcError']:
        return None

    @classmethod
    def from_json(cls, json_data: JsonT) -> 'JsonRpcError':
        """
        Deserializes an error from json data. If data format is not correct :py:class:`ValueError` is raised.

        :param json_data: json data the error to be deserialized from

        :returns: deserialized error
        :raises: :py:class:`pjrpc.common.exceptions.DeserializationError` if format is incorrect
        """

        try:
            if not isinstance(json_data, dict):
                raise DeserializationError("data must be of type dict")

            code = json_data['code']
            if not isinstance(code, int):
                raise DeserializationError("field 'code' must be of type integer")

            message = json_data['message']
            if not isinstance(message, str):
                raise DeserializationError("field 'message' must be of type string")

            data = json_data.get('data', UNSET)

            if typed_error := cls.get_typed_error_by_code(code, message, data):
                return typed_error
            else:
                return cls(code, message, data)

        except KeyError as e:
            raise DeserializationError(f"required field {e} not found") from e

    def to_json(self) -> JsonT:
        """
        Serializes the error into a dict.

        :returns: serialized error
        """

        json: dict[str, JsonT] = {
            'code': self.code,
            'message': self.message,
        }
        if self.data is not UNSET:
            json.update(data=self.data)

        return json

    def __str__(self) -> str:
        return f"({self.code}) {self.message}"


class ParseError:
    """
    Invalid JSON was received by the server.
    An error occurred on the server while parsing the JSON text.
    """

    CODE: ClassVar[int] = -32700
    MESSAGE: ClassVar[str] = 'Parse error'


class InvalidRequestError:
    """
    The JSON sent is not a valid request object.
    """

    CODE: ClassVar[int] = -32600
    MESSAGE: ClassVar[str] = 'Invalid Request'


class MethodNotFoundError:
    """
    The method does not exist / is not available.
    """

    CODE: ClassVar[int] = -32601
    MESSAGE: ClassVar[str] = 'Method not found'


class InvalidParamsError:
    """
    Invalid method parameter(s).
    """

    CODE: ClassVar[int] = -32602
    MESSAGE: ClassVar[str] = 'Invalid params'


class InternalError:
    """
    Internal JSON-RPC error.
    """

    CODE: ClassVar[int] = -32603
    MESSAGE: ClassVar[str] = 'Internal error'


class ServerError:
    """
    Reserved for implementation-defined server-errors.
    Codes from -32000 to -32099.
    """

    CODE: ClassVar[int] = -32000
    MESSAGE: ClassVar[str] = 'Server error'
