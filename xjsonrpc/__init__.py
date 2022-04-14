"""
Extensible `JSON-RPC <https://www.jsonrpc.org>`_ client/server library.
"""

from xjsonrpc.common import exceptions
from xjsonrpc.common import Request, BatchRequest
from xjsonrpc.common import Response, BatchResponse
from xjsonrpc.common import JSONEncoder


from xjsonrpc.__about__ import (
    __title__,
    __description__,
    __url__,
    __version__,
    __author__,
    __email__,
    __license__,
)

# shortcuts
exc = exceptions

__all__ = [
    '__title__',
    '__description__',
    '__url__',
    '__version__',
    '__author__',
    '__email__',
    '__license__',

    'exceptions',
    'exc',
    'Request',
    'Response',
    'BatchRequest',
    'Response',
    'Response',
    'BatchResponse',
    'JSONEncoder',
]
