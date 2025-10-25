import asyncio
import logging

import aio_pika
from yarl import URL

import pjrpc
from pjrpc.server.integration import aio_pika as integration

methods = pjrpc.server.MethodRegistry()


@methods.add(pass_context='message')
def sum(message: aio_pika.IncomingMessage, a: int, b: int) -> int:
    return a + b


@methods.add(pass_context=True)
def sub(context: aio_pika.IncomingMessage, a: int, b: int) -> int:
    return a - b


@methods.add()
async def ping() -> None:
    logging.info("ping")


executor = integration.Executor(URL('amqp://guest:guest@localhost:5672/v1'), request_queue_name='math-service')
executor.dispatcher.add_methods(methods)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    loop = asyncio.get_event_loop()

    loop.run_until_complete(executor.start())
    try:
        loop.run_forever()
    finally:
        loop.run_until_complete(executor.shutdown())
