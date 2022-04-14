import uuid

import kombu

import xjsonrpc
from xjsonrpc.server.integration import kombu as integration

methods = xjsonrpc.server.MethodRegistry()


@methods.add(context='message')
def add_user(message: kombu.Message, user: dict):
    user_id = uuid.uuid4().hex

    return {'id': user_id, **user}


@methods.add  # type: ignore
def sum(a: int, b: int) -> int:
    """RPC method sum(a, b) for kombu_client.py and aio_pika_client.py"""
    return a + b


@methods.add  # type: ignore
def tick() -> None:
    """RPC notification "tick" for kombu_client.py and aio_pika_client.py"""
    print("received tick")


# Note: The server may not work well with examples/kombu_client.py yet.
# Use with examples/aio_pika_client.py in case server or client gets stuck.

if __name__ == "__main__":
    executor = integration.Executor(
        "amqp://guest:guest@localhost:5672/v1",
        queue_name="jsonrpc",
        # Compatible with queue of examples/aio_pika_*
        # and works better with examples/kombu_client.py:
        queue_args={"durable": False},
    )
    executor.dispatcher.add_methods(methods)
    executor.run()
