"""
Client and server common functions, types and classes that implements JSON-RPC protocol itself
and agnostic to any transport protocol layer (http, socket, amqp) and server-side implementation.
"""

from . import exceptions, generators, typedefs
from .common import UNSET, JsonT, MaybeSet, UnsetType
from .encoder import JSONEncoder
from .exceptions import JsonRpcError
from .request import AbstractRequest, BatchRequest, Request
from .response import AbstractResponse, BatchResponse, Response

DEFAULT_CONTENT_TYPE = 'application/json'
'''default JSON-RPC client/server content type'''  # for sphinx autodoc

REQUEST_CONTENT_TYPES = ('application/json', 'application/json-rpc', 'application/jsonrequest')
'''allowed JSON-RPC server requests content types'''  # for sphinx autodoc

RESPONSE_CONTENT_TYPES = ('application/json', 'application/json-rpc')
'''allowed JSON-RPC client responses content types'''  # for sphinx autodoc


__all__ = [
    'AbstractRequest',
    'AbstractResponse',
    'BatchRequest',
    'BatchResponse',
    'DEFAULT_CONTENT_TYPE',
    'exceptions',
    'generators',
    'JSONEncoder',
    'JsonRpcError',
    'JsonT',
    'MaybeSet',
    'Request',
    'REQUEST_CONTENT_TYPES',
    'Response',
    'RESPONSE_CONTENT_TYPES',
    'typedefs',
    'UNSET',
    'UnsetType',
]
