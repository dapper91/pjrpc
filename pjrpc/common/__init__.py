"""
Client and server common functions, types and classes that implements JSON-RPC protocol itself
and agnostic to any transport protocol layer (http, socket, amqp) and server-side implementation.
"""

from . import generators, typedefs
from .common import UNSET, JSONEncoder, UnsetType
from .v20 import AbstractRequest, AbstractResponse, BatchRequest, BatchResponse, Request, Response

DEFAULT_CONTENT_TYPE = 'application/json'
'''default JSON-RPC client/server content type'''  # for sphinx autodoc

REQUEST_CONTENT_TYPES = ('application/json', 'application/json-rpc', 'application/jsonrequest')
'''allowed JSON-RPC server requests content types'''  # for sphinx autodoc

RESPONSE_CONTENT_TYPES = ('application/json', 'application/json-rpc')
'''allowed JSON-RPC client responses content types'''  # for sphinx autodoc


def set_default_content_type(content_type: str) -> None:
    """
    Sets default json-rpc client request / json-rpc server response content type.
    """

    global DEFAULT_CONTENT_TYPE

    DEFAULT_CONTENT_TYPE = content_type


__all__ = [
    'AbstractRequest',
    'AbstractResponse',
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
    'typedefs',
    'set_default_content_type',
]
