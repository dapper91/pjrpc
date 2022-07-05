.. _retires:

Retries
=======

``pjrpc`` supports request retries based on response code or received exception using customizable backoff strategy.
``pjrpc`` provides several built-in backoff algorithms (see :py:mod:`pjrpc.client.retry`), but you can
implement your own one like this:

.. code-block:: python

    import dataclasses as dc
    import random
    from pjrpc.client.retry import Backoff

    @dc.dataclass(frozen=True)
    class RandomBackoff(Backoff):
        def __call__(self) -> Iterator[float]:
            return (random.random() for _ in range(self.attempts))


Retry strategy can be configured for all client requests by passing a strategy to a client constructor
as a `retry_strategy` argument or for a particular request as a `_retry_strategy` when calling `send` method.

The following example illustrate request retries api usage:

.. code-block:: python

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
                _retry_strategy=RetryStrategy(
                    exceptions={TimeoutError},
                    codes={2001},
                    backoff=ExponentialBackoff(
                        attempts=3, base=1.0, factor=2.0, jitter=lambda: random.gauss(mu=0.5, sigma=0.1),
                    ),
                ),
            )
            print(f"1 + 2 = {response.result}")

            result = await client.proxy.sum(1, 2)
            print(f"1 + 2 = {result}")


    asyncio.run(main())
