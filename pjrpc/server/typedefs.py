from __future__ import annotations

from typing import Any, Awaitable, Callable, Optional, Union

import pjrpc.common.exceptions
from pjrpc.common import Request, Response, UnsetType

__all__ = [
    'AsyncMiddlewareType',
    'AsyncErrorHandlerType',
    'MiddlewareType',
    'ErrorHandlerType',
]

AsyncMiddlewareType = Callable[
    [Request, Optional[Any], Callable[[Request, Optional[Any]], Union[UnsetType, Response]]],
    Awaitable[Union[UnsetType, Response]],
]
'''Asynchronous middleware type'''  # for sphinx autodoc

AsyncErrorHandlerType = Callable[
    [Request, Optional[Any], pjrpc.exceptions.JsonRpcError],
    Awaitable[pjrpc.exceptions.JsonRpcError],
]
'''Asynchronous server error handler'''  # for sphinx autodoc


MiddlewareType = Callable[
    [Request, Optional[Any], Callable[[Request, Optional[Any]], Union[UnsetType, Response]]],
    Union[UnsetType, Response],
]
'''Synchronous middleware type'''  # for sphinx autodoc

ErrorHandlerType = Callable[
    [Request, Optional[Any], pjrpc.exceptions.JsonRpcError],
    pjrpc.exceptions.JsonRpcError,
]
'''Synchronous server error handler'''  # for sphinx autodoc
