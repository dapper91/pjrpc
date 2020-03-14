"""
Builtin request id generators. Implements several identifier types and generation strategies.
"""

import itertools as it
import random as _random
import string
import uuid as _uuid
from typing import Generator


def sequential(start: int = 1, step: int = 1) -> Generator[int, None, None]:
    """
    Sequential id generator. Returns consecutive values starting from `start` with step `step`.
    """

    yield from it.count(start, step)


def randint(a: int, b: int) -> Generator[int, None, None]:
    """
    Random integer id generator. Returns random integers between `a` and `b`.
    """

    while True:
        yield _random.randint(a, b)


def random(length: int = 8, chars: str = string.digits + string.ascii_lowercase) -> Generator[str, None, None]:
    """
    Random string id generator. Returns random strings of length `length` using alphabet `chars`.
    """

    while True:
        yield ''.join((_random.choice(chars) for _ in range(length)))


def uuid() -> Generator[_uuid.UUID, None, None]:
    """
    UUID id generator. Returns random UUIDs.
    """

    while True:
        yield _uuid.uuid4()
