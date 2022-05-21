from __future__ import annotations

from typing import Any, Callable, Dict, List, Set, Tuple, TypeVar, Union

__all__ = [
    'JsonRpcParams',
    'JsonRpcRequestId',
    'Json',
    'MethodType',
    'Func',
]

JsonRpcParams = Union[List[Any], Tuple[Any, ...], Dict[str, Any]]
'''JSON-RPC params type'''  # for sphinx autodoc

JsonRpcRequestId = Union[str, int]
'''JSON-RPC identifier type'''  # for sphinx autodoc

Json = Union[List[Any], Tuple[Any, ...], Set[Any], Dict[str, Any], None]
'''JSON type'''  # for sphinx autodoc

MethodType = Callable[..., Any]
'''Method type'''  # for sphinx autodoc

Func = TypeVar('Func', bound=MethodType)
'''Function type'''  # for sphinx autodoc
