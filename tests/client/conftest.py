import pytest
from aiointercept import aiointercept


@pytest.fixture
async def aiointerceptor():
    async with aiointercept(mock_external_urls=True) as mocker:
        yield mocker
