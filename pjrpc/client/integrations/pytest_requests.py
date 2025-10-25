import functools as ft
from typing import Generator

import pytest

from .pytest import PjRpcMocker

PjRpcRequestsMocker = ft.partial(PjRpcMocker, target='pjrpc.client.backend.requests.Client._request')


@pytest.fixture
def pjrpc_requests_mocker() -> Generator[PjRpcMocker, None, None]:
    """
    Requests client mocking fixture.
    """

    with PjRpcRequestsMocker() as mocker:
        yield mocker
