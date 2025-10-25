from typing import Union

__all__ = [
    'JsonRpcParamsT',
    'JsonRpcRequestIdT',
    'JsonT',
]

JsonT = Union[str, int, float, bool, None, list['JsonT'], tuple['JsonT', ...], dict[str, 'JsonT']]
'''JSON type'''  # for sphinx autodoc

JsonRpcRequestIdT = Union[str, int]
'''JSON-RPC identifier type'''  # for sphinx autodoc

JsonRpcParamsT = Union[list[JsonT], tuple[JsonT, ...], dict[str, JsonT]]
'''JSON-RPC parameters type'''  # for sphinx autodoc
