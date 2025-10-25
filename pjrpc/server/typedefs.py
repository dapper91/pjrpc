from typing import Awaitable, Callable, Protocol, TypeVar

from pjrpc.common import MaybeSet, Request, Response

__all__ = [
    'AsyncHandlerType',
    'AsyncMiddlewareType',
    'ContextType',
    'HandlerType',
    'MiddlewareResponse',
    'MiddlewareType',
]


ContextType = TypeVar('ContextType')
'''Context argument for RPC methods and middlewares'''  # for sphinx autodoc

AsyncHandlerType = Callable[[Request, ContextType], Awaitable[MaybeSet[Response]]]
'''Async RPC handler method, passed to middlewares'''  # for sphinx autodoc

HandlerType = Callable[[Request, ContextType], MaybeSet[Response]]
'''Blocking RPC handler method, passed to middlewares'''  # for sphinx autodoc

MiddlewareResponse = MaybeSet[Response]
'''middlewares and handlers return Response or UnsetType'''  # for sphinx autodoc


class AsyncMiddlewareType(Protocol[ContextType]):
    """
    Asynchronous middleware type
    """

    async def __call__(
        self,
        request: Request,
        context: ContextType,
        handler: AsyncHandlerType[ContextType],
    ) -> MaybeSet[MiddlewareResponse]:
        pass


class MiddlewareType(Protocol[ContextType]):
    """
    Synchronous middleware type
    """

    async def __call__(
        self,
        request: Request,
        context: ContextType,
        handler: HandlerType[ContextType],
    ) -> MaybeSet[MiddlewareResponse]:
        pass
