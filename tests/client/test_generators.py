import random
import string
import uuid

import pytest
from pjrpc.common import generators


@pytest.mark.parametrize(
    'start, step, length, result', [
        (0, 1, 3, [0, 1, 2]),
        (1, 2, 3, [1, 3, 5]),
    ],
)
def test_sequential(start, step, length, result):
    gen = generators.sequential(start, step)
    assert [next(gen) for _ in range(length)] == result


@pytest.mark.parametrize(
    'a, b, length, seed, result', [
        (0, 10, 5, 1, [2, 9, 1, 4, 1]),
    ],
)
def test_randint(a, b, length, seed, result):
    random.seed(seed)
    gen = generators.randint(a, b)
    assert [next(gen) for _ in range(length)] == result


@pytest.mark.parametrize(
    'length, chars, seed, result', [
        (5, string.ascii_lowercase, 1, ['eszyc', 'idpyo', 'pumzg', 'dpamn', 'tyyaw']),
        (5, string.digits, 1, ['29141', '77763', '17066', '90743', '91500']),
    ],
)
def test_random(length, chars, seed, result):
    random.seed(seed)
    gen = generators.random(length, chars)
    assert [next(gen) for _ in range(length)] == result


def test_uuid(mocker):
    mocked_uuid = uuid.UUID('226a2c23-c98b-4729-b398-0dae550e99ff')
    mocker.patch('uuid.uuid4', return_value=mocked_uuid)

    gen = generators.uuid()
    assert [next(gen) for _ in range(2)] == [mocked_uuid] * 2
