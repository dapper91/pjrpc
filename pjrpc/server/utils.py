from typing import Any, Dict


def get_meta(instance: Any) -> Dict[str, Any]:
    """
    Returns object pjrpc metadata.
    """

    return getattr(instance, '__pjrpc_meta__', {})


def set_meta(instance: Any, **meta) -> Dict[str, Any]:
    """
    Updates object pjrpc metadata.
    """

    if not hasattr(instance, '__pjrpc_meta__'):
        instance.__pjrpc_meta__ = {}

    instance.__pjrpc_meta__.update(meta)

    return instance.__pjrpc_meta__
