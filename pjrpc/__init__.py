"""
Extensible `JSON-RPC <https://www.jsonrpc.org>`_ client/server library.
"""

from pjrpc.__about__ import __author__, __description__, __email__, __license__, __title__, __url__, __version__
from pjrpc.common import BatchRequest, BatchResponse, JSONEncoder, Request, Response, exceptions

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
