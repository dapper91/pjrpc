import pytest
from aioresponses import aioresponses


@pytest.fixture
def responses():
    with aioresponses() as mocker:
        yield mocker
