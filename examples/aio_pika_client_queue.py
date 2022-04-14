#!/usr/bin/env python
import asyncio
import logging
import xjsonrpc.client.backend.aio_pika


async def client_with_specific_queue() -> None:
    """aio_pika client demonstrating the use of a specific result_queue"""
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    client = xjsonrpc.client.backend.aio_pika.Client(
        broker_url="amqp://guest:guest@localhost:5672/v1",
        queue_name="jsonrpc",
        # By default, an automatically-generated result queue is created.
        # This shows using a specific queue with specific properities instead:
        result_queue_name="xjsonrpc-aio_pika-example-jsonrpc-results",
        result_queue_args={
            "exclusive": True,
            "auto_delete": True,
            "durable": False,
            "arguments": None,
        },
    )
    await client.connect()

    result = await client.proxy.sum(1, 2)
    print(f"1 + 2 = {result}")

    await client.notify("tick")
    await client.close()


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(client_with_specific_queue())
