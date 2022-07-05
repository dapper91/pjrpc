import asyncio
import random

import pjrpc
from pjrpc.client.backend import aiohttp as pjrpc_client
from pjrpc.client.retry import ExponentialBackoff, PeriodicBackoff, RetryStrategy


async def main():
    default_retry_strategy = RetryStrategy(
        exceptions={TimeoutError},
        backoff=PeriodicBackoff(attempts=3, interval=1.0, jitter=lambda: random.gauss(mu=0.5, sigma=0.1)),
    )

    async with pjrpc_client.Client('http://localhost/api/v1', retry_strategy=default_retry_strategy) as client:
        response = await client.send(
            pjrpc.Request('sum', params=[1, 2], id=1),
            _retries=RetryStrategy(
                exceptions={TimeoutError},
                codes={2001},
                backoff=ExponentialBackoff(
                    attempts=3, base=1.0, factor=2.0, jitter=lambda: random.gauss(mu=0.5, sigma=0.1),
                ),
            ),
        )
        print(f"1 + 2 = {response.result}")

        result = await client('sum', a=1, b=2)
        print(f"1 + 2 = {result}")

        result = await client.proxy.sum(1, 2)
        print(f"1 + 2 = {result}")

        await client.notify('tick')


asyncio.run(main())
