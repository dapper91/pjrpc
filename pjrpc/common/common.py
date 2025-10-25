import enum
from typing import Any, Literal, TypeVar, Union


class UnsetType(enum.Enum):
    """
    `Sentinel <https://en.wikipedia.org/wiki/Sentinel_value>`_ object.
    Used to distinct unset (missing) values from ``None`` ones.
    """

    UNSET = "UNSET"

    def __bool__(self) -> Literal[False]:
        return False

    def __repr__(self) -> str:
        return "UNSET"

    def __str__(self) -> str:
        return repr(self)


UNSET: UnsetType = UnsetType.UNSET

MaybeSetType = TypeVar('MaybeSetType')
MaybeSet = Union[UnsetType, MaybeSetType]

JsonT = Any
