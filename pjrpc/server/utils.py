from typing import Any, Callable, Optional


def remove_prefix(s: str, prefix: str) -> str:
    """
    Removes a prefix from a string.

    :param s: string to be processed
    :param prefix: prefix to be removed
    :return: processed string
    """

    if s.startswith(prefix):
        return s[len(prefix):]
    else:
        return s


def remove_suffix(s: str, suffix: str) -> str:
    """
    Removes a suffix from a string.

    :param s: string to be processed
    :param suffix: suffix to be removed
    :return: processed string
    """

    if suffix and s.endswith(suffix):
        return s[0:-len(suffix)]
    else:
        return s


def join_path(path: str, *paths: str) -> str:
    result = path
    for path in paths:
        if path:
            result = f'{result.rstrip("/")}/{path.lstrip("/")}'

    return result


ExcludeFunc = Callable[[int, str, Optional[type[Any]], Optional[Any]], bool]


def exclude_positional_param(param_index: int) -> ExcludeFunc:
    def exclude(index: int, name: str, typ: Optional[type[Any]], default: Optional[Any]) -> bool:
        return index == param_index

    return exclude


def exclude_named_param(param_name: str) -> ExcludeFunc:
    def exclude(index: int, name: str, typ: Optional[type[Any]], default: Optional[Any]) -> bool:
        return name == param_name

    return exclude
