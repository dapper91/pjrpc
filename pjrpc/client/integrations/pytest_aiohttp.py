import functools as ft
from typing import Generator

import pytest

from .pytest import PjRpcMocker

PjRpcAiohttpMocker = ft.partial(PjRpcMocker, target='pjrpc.client.backend.aiohttp.Client._request')


@pytest.fixture
def pjrpc_aiohttp_mocker() -> Generator[PjRpcMocker, None, None]:
    """
    Aiohttp client mocking fixture.
    """

    with PjRpcAiohttpMocker() as mocker:
        yield mocker
