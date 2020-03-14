"""
Extensible `JSON-RPC <https://www.jsonrpc.org>`_ client/server library.
"""

from pjrpc.common import exceptions
from pjrpc.common import Request, BatchRequest
from pjrpc.common import Response, BatchResponse
from pjrpc.common import JSONEncoder


from pjrpc.__about__ import (
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
