import asyncio
import uuid

import aio_pika

import pjrpc
from pjrpc.server.integration import aio_pika as integration

methods = pjrpc.server.MethodRegistry()


@methods.add
def sum(a, b):
    """RPC method implementing examples/aio_pika_client.py's calls to sum(1, 2) -> 3"""
    return a + b


@methods.add
def tick():
    """RPC method implementing examples/aio_pika_client.py's notification 'tick'"""
    print("examples/aio_pika_server.py: received tick")


@methods.add(context='message')
def add_user(message: aio_pika.IncomingMessage, user: dict):
    user_id = uuid.uuid4().hex

    return {'id': user_id, **user}


executor = integration.Executor('amqp://guest:guest@localhost:5672/v1', queue_name='jsonrpc')
executor.dispatcher.add_methods(methods)

if __name__ == "__main__":
    loop = asyncio.get_event_loop()

    loop.run_until_complete(executor.start())
    try:
        loop.run_forever()
    finally:
        loop.run_until_complete(executor.shutdown())
