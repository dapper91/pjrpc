import asyncio
import logging
import uuid
from dataclasses import dataclass

import aio_pika
from yarl import URL

import pjrpc
from pjrpc.server.integration import aio_pika as integration


@dataclass
class UserInfo:
    """User information dataclass for the add_user example RPC call"""

    username: str
    name: str
    age: int


@dataclass
class AddedUser(UserInfo):
    """User information dataclass (with uuid) for the add_user example RPC call"""

    uuid: uuid.UUID


methods = pjrpc.server.MethodRegistry()


@methods.add
def sum(a: int, b: int) -> int:
    """RPC method implementing examples/aio_pika_client.py's calls to sum(1, 2) -> 3"""
    return a + b


@methods.add
def tick() -> None:
    """RPC method implementing examples/aio_pika_client.py's notification 'tick'"""
    print("examples/aio_pika_server.py: received tick")


@methods.add(context='message')
def add_user(message: aio_pika.IncomingMessage, user_info: UserInfo) -> AddedUser:
    """Simluate the creation of a user: Receive user info and return it with an uuid4.
    :param UserInfo user_info: user data
    :returns: user_info with a randomly generated uuid4 added
    :rtype: AddedUser"""
    return AddedUser(**user_info.__dict__, uuid=uuid.uuid4())


executor = integration.Executor(
    broker_url=URL('amqp://guest:guest@localhost:5672/v1'), queue_name='jsonrpc',
)
executor.dispatcher.add_methods(methods)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logging.info("Example result from a local call to add_user():")
    logging.info(add_user(None, UserInfo("username", "firstname lastname", 18)))
    loop = asyncio.new_event_loop()

    loop.run_until_complete(executor.start())
    try:
        loop.run_forever()
    finally:
        loop.run_until_complete(executor.shutdown())
