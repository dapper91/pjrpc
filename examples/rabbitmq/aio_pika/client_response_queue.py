#!/usr/bin/env python
"""By default, RabbitMQ JSON-RPC clients generate a temporary result queue
for their requests, but in very special cases, the client may want to choose
a specific result queue.

This example shows using a specific queue with specific properties as well."""
import asyncio
import logging

from yarl import URL

import pjrpc.client.backend.aio_pika


async def client_with_specific_queue() -> None:
    """aio_pika client demonstrating the use of a specific result_queue"""
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    client = pjrpc.client.backend.aio_pika.Client(
        broker_url=URL("amqp://guest:guest@localhost:5672/v1"),
        queue_name="jsonrpc",
        result_queue_name="pjrpc-aio_pika-example-jsonrpc-results",
        result_queue_args={
            "exclusive": True,
            "auto_delete": True,
            "durable": True,
            "arguments": None,
        },
    )
    await client.connect()

    result = await client.proxy.sum(1, 2)
    print(f"1 + 2 = {result}")

    await client.notify("tick")
    await client.notify("schedule_shutdown")
    await client.close()


if __name__ == "__main__":
    asyncio.run(client_with_specific_queue())
