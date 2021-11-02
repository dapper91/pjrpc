"""
Client and server common functions, types and classes that implements JSON-RPC protocol itself
and agnostic to any transport protocol layer (http, socket, amqp) and server-side implementation.
"""

from . import generators
from .common import UNSET, UnsetType, JSONEncoder
from .v20 import Request, Response, BatchRequest, BatchResponse

DEFAULT_CONTENT_TYPE = 'application/json'
REQUEST_CONTENT_TYPES = ('application/json', 'application/json-rpc', 'application/jsonrequest')
RESPONSE_CONTENT_TYPES = ('application/json', 'application/json-rpc')


def set_default_content_type(content_type: str) -> None:
    """
    Sets default json-rpc client request / json-rpc server response content type.
    """

    global DEFAULT_CONTENT_TYPE

    DEFAULT_CONTENT_TYPE = content_type


__all__ = [
    'Request',
    'Response',
    'BatchRequest',
    'BatchResponse',
    'UNSET',
    'UnsetType',
    'JSONEncoder',
    'DEFAULT_CONTENT_TYPE',
    'REQUEST_CONTENT_TYPES',
    'RESPONSE_CONTENT_TYPES',
    'generators',
]
