import asyncio
import random

import aiohttp

import pjrpc
from pjrpc.client.backend import aiohttp as pjrpc_client
from pjrpc.client.retry import AsyncRetryMiddleware, ExponentialBackoff, RetryStrategy


async def main():
    default_retry_strategy = RetryStrategy(
        exceptions={TimeoutError},
        backoff=ExponentialBackoff(attempts=3, base=1.0, factor=2.0, jitter=lambda n: random.gauss(mu=0.5, sigma=0.1)),
    )

    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=0.2)) as session:
        async with pjrpc_client.Client(
            'http://localhost:8080/api/v1',
            session=session,
            middlewares=[AsyncRetryMiddleware(default_retry_strategy)],
        ) as client:
            response = await client.send(pjrpc.Request('sum', params=[1, 2], id=1))
            print(f"1 + 2 = {response.result}")

            result = await client.proxy.sum(1, 2)
            print(f"1 + 2 = {result}")


asyncio.run(main())
