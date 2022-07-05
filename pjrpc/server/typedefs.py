from __future__ import annotations

from typing import Any, Awaitable, Callable, Optional, Union

import pjrpc.common.exceptions
from pjrpc.common import Request, Response, UnsetType

__all__ = [
    'AsyncErrorHandlerType',
    'AsyncMiddlewareType',
    'AsyncHandlerType',
    'MiddlewareResponse',
    'MiddlewareType',
    'ErrorHandlerType',
    'ResponseOrUnset',
    'ContextType',
]


ContextType = Optional[Any]
'''Context argument for RPC methods and middlewares'''  # for sphinx autodoc

ResponseOrUnset = Union[UnsetType, Response]
'''Return value of RPC handlers and middlewares'''  # for sphinx autodoc

AsyncHandlerType = Callable[[Request, ContextType], Awaitable[ResponseOrUnset]]
'''Async RPC handler method, passed to middlewares'''  # for sphinx autodoc

HandlerType = Callable[[Request, ContextType], ResponseOrUnset]
'''Blocking RPC handler method, passed to middlewares'''  # for sphinx autodoc

MiddlewareResponse = Union[UnsetType, Response]
'''middlewares and handlers return Response or UnsetType'''  # for sphinx autodoc

AsyncMiddlewareType = Callable[
    [Request, ContextType, AsyncHandlerType],
    Awaitable[MiddlewareResponse],
]
'''Asynchronous middleware type'''  # for sphinx autodoc

AsyncErrorHandlerType = Callable[
    [Request, ContextType, pjrpc.exceptions.JsonRpcError],
    Awaitable[pjrpc.exceptions.JsonRpcError],
]
'''Asynchronous server error handler'''  # for sphinx autodoc


MiddlewareType = Callable[
    [Request, ContextType, HandlerType],
    MiddlewareResponse,
]
'''Synchronous middleware type'''  # for sphinx autodoc

ErrorHandlerType = Callable[
    [Request, ContextType, pjrpc.exceptions.JsonRpcError],
    pjrpc.exceptions.JsonRpcError,
]
'''Synchronous server error handler'''  # for sphinx autodoc
