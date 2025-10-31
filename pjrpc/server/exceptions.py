import dataclasses as dc
from typing import Any, ClassVar, Optional

from pjrpc.common import UNSET, JsonT, MaybeSet, exceptions
from pjrpc.common.exceptions import BaseError, DeserializationError, IdentityError, ProtocolError

__all__ = [
    'BaseError',
    'DeserializationError',
    'IdentityError',
    'InternalError',
    'InvalidParamsError',
    'InvalidRequestError',
    'JsonRpcError',
    'MethodNotFoundError',
    'ParseError',
    'ProtocolError',
    'ServerError',
    'TypedError',
]


@dc.dataclass(frozen=True)
class JsonRpcError(exceptions.JsonRpcError):
    """
    Server JSON-RPC error.
    """

    # typed subclasses error mapping
    __TYPED_ERRORS__: ClassVar[dict[int, type['TypedError']]] = {}

    @classmethod
    def get_typed_error_by_code(cls, code: int, message: str, data: MaybeSet[JsonT]) -> Optional['JsonRpcError']:
        if error_cls := cls.__TYPED_ERRORS__.get(code):
            return error_cls(message, data)
        else:
            return None


class TypedError(JsonRpcError):
    """
    Typed JSON-RPC error.
    Must not be instantiated directly, only subclassed.
    """

    # a number that indicates the error type that occurred
    CODE: ClassVar[int]

    # a string providing a short description of the error.
    # the message SHOULD be limited to a concise single sentence.
    MESSAGE: ClassVar[str]

    def __init_subclass__(cls, base: bool = False, **kwargs: Any):
        super().__init_subclass__(**kwargs)

        if issubclass(cls, TypedError) and (code := getattr(cls, 'CODE', None)) is not None:
            cls.__TYPED_ERRORS__[code] = cls

    def __init__(self, message: Optional[str] = None, data: MaybeSet[JsonT] = UNSET):
        super().__init__(self.CODE, message or self.MESSAGE, data)


class ParseError(TypedError, exceptions.ParseError):
    """
    Invalid JSON was received by the server.
    An error occurred on the server while parsing the JSON text.
    """


class InvalidRequestError(TypedError, exceptions.InvalidRequestError):
    """
    The JSON sent is not a valid request object.
    """


class MethodNotFoundError(TypedError, exceptions.MethodNotFoundError):
    """
    The method does not exist / is not available.
    """


class InvalidParamsError(TypedError, exceptions.InvalidParamsError):
    """
    Invalid method parameter(s).
    """


class InternalError(TypedError, exceptions.InternalError):
    """
    Internal JSON-RPC error.
    """


class ServerError(TypedError, exceptions.ServerError):
    """
    Reserved for implementation-defined server-errors.
    Codes from -32000 to -32099.
    """
