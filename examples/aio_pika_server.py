#!/usr/bin/env python
import asyncio
import logging
import uuid

import aio_pika

import pjrpc
from pjrpc.server.integration import aio_pika as integration

methods = pjrpc.server.MethodRegistry()
info = logging.getLogger().info


@methods.add
def sum(a: int, b: int) -> int:
    """RPC method implementing examples/aio_pika_client.py's calls to sum(1, 2) -> 3"""
    return a + b


@methods.add
def tick() -> None:
    """RPC method implementing examples/aio_pika_client.py's notification 'tick'"""
    print("examples/aio_pika_server.py: received tick")


@methods.add(context='message')
def schedule_shutdown(message: aio_pika.IncomingMessage) -> None:
    """Schedule a shutdown, allows for an ack and response delivery"""
    info("received command to schedule a shutdown as notification from RPC client:")
    info(f"Stopping server in 0.2, message id was: {message.message_id}")
    asyncio.get_running_loop().call_later(0.2, loop.stop)


@methods.add(context='message')
def add_user(message: aio_pika.IncomingMessage, user: dict):
    user_id = uuid.uuid4().hex

    return {'id': user_id, **user}


executor = integration.Executor('amqp://guest:guest@localhost:5672/v1', queue_name='jsonrpc')
executor.dispatcher.add_methods(methods)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(filename)s:%(funcName)s: %(message)s")
    loop = asyncio.get_event_loop()

    loop.run_until_complete(executor.start())
    try:
        loop.run_forever()
    finally:
        loop.run_until_complete(executor.shutdown())
