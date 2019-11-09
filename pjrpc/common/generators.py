"""
Builtin request id generators. Implements several identifier types and generation strategies.
"""

import itertools as it
import random as _random
import string
import uuid as _uuid


def sequential(start=1, step=1):
    """
    Sequential id generator. Returns consecutive values starting from `start` with step `step`.
    """

    yield from it.count(start, step)


def randint(a, b):
    """
    Random integer id generator. Returns random integers between `a` and `b`.
    """

    while True:
        yield _random.randint(a, b)


def random(length=8, chars=string.digits + string.ascii_lowercase):
    """
    Random string id generator. Returns random strings of length `length` using alphabet `chars`.
    """

    while True:
        yield ''.join((_random.choice(chars) for _ in range(length)))


def uuid():
    """
    UUID id generator. Returns random UUIDs.
    """

    while True:
        yield _uuid.uuid4()
