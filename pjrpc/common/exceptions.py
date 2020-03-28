"""
Definition of package exceptions and JSON-RPC protocol errors.
"""

from typing import Any, Dict, Optional, Type, Union

from .common import UNSET, Json, UnsetType


class BaseError(Exception):
    """
    Base package error. All package errors are inherited from it.
    """


class IdentityError(BaseError):
    """
    Raised when a batch requests/responses identifiers are not unique or missing.
    """


class DeserializationError(BaseError, ValueError):
    """
    Request/response deserializatoin error.
    Raised when request/response json has incorrect format.
    """


class JsonRpcErrorMeta(type):
    """
    :py:class:`pjrpc.common.exceptions.JsonRpcError` metaclass.
    Builds a mapping from an error code number to an error class
    inherited from a :py:class:`pjrpc.common.exceptions.JsonRpcError`.
    """

    __errors_mapping__: Dict[int, Type['JsonRpcError']] = {}

    def __new__(mcs, name: str, bases: tuple, dct: dict) -> Type['JsonRpcError']:
        cls: Type[JsonRpcError] = super().__new__(mcs, name, bases, dct)
        if hasattr(cls, 'code') and cls.code is not None:
            mcs.__errors_mapping__[cls.code] = cls

        return cls


class JsonRpcError(BaseError, metaclass=JsonRpcErrorMeta):
    """
    `JSON-RPC <https://www.jsonrpc.org>`_ protocol error.
    For more information see `Error object <https://www.jsonrpc.org/specification#error_object>`_.
    All JSON-RPC protocol errors are inherited from it.

    :param code: number that indicates the error type
    :param message: short description of the error
    :param data: value that contains additional information about the error. May be omitted.
    """

    # a number that indicates the error type that occurred
    code = None

    # a string providing a short description of the error.
    # the message SHOULD be limited to a concise single sentence.
    message = None

    @classmethod
    def from_json(cls, json_data: Json) -> 'JsonRpcError':
        """
        Deserializes an error from json data. If data format is not correct :py:class:`ValueError` is raised.

        :param json_data: json data the error to be deserialized from

        :returns: deserialized error
        :raises: :py:class:`pjrpc.common.exception.DeserializationError` if format is incorrect
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

            error_class = cls.get_error_cls(code, cls)

            return error_class(code, message, json_data.get('data', UNSET))
        except KeyError as e:
            raise DeserializationError(f"required field {e} not found") from e

    @classmethod
    def get_error_cls(cls, code: int, default: Any) -> Type['JsonRpcError']:
        return type(cls).__errors_mapping__.get(code, default)

    def __init__(self, code: Optional[int] = None, message: Optional[str] = None, data: Union[UnsetType, Any] = UNSET):
        assert code or self.code, "code is not provided"
        assert message or self.message, "message is not provided"

        self.code = self.code or code
        self.message = self.message or message
        self.data = data

        super().__init__(code, message)

    def __str__(self) -> str:
        return "({code}) {message}".format(code=self.code, message=self.message)

    def __repr__(self) -> str:
        return "{class_name}(code={code}, message={message}, data={data})".format(
            class_name=self.__class__.__name__, code=repr(self.code), message=repr(self.message), data=repr(self.data),
        )

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, JsonRpcError):
            return NotImplemented

        return (self.code, self.message, self.data) == (other.code, other.message, other.data)

    def to_json(self) -> Json:
        """
        Serializes the error to a dict.

        :returns: serialized error
        """

        json: Dict[str, Json] = {
            'code': self.code,
            'message': self.message,
        }
        if self.data is not UNSET:
            json.update(data=self.data)

        return json


class ClientError(JsonRpcError):
    """
    Raised when a client sent an incorrect request.
    """


class ParseError(ClientError):
    """
    Invalid JSON was received by the server.
    An error occurred on the server while parsing the JSON text.
    """

    code = -32700
    message = 'Parse error'


class InvalidRequestError(ClientError):
    """
    The JSON sent is not a valid request object.
    """

    code = -32600
    message = 'Invalid Request'


class MethodNotFoundError(ClientError):
    """
    The method does not exist / is not available.
    """

    code = -32601
    message = 'Method not found'


class InvalidParamsError(ClientError):
    """
    Invalid method parameter(s).
    """

    code = -32602
    message = 'Invalid params'


class InternalError(JsonRpcError):
    """
    Internal JSON-RPC error.
    """

    code = -32603
    message = 'Internal error'


class ServerError(JsonRpcError):
    """
    Reserved for implementation-defined server-errors.
    Codes from -32000 to -32099.
    """

    code = -32000
    message = 'Server error'
