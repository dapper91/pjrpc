#!/usr/bin/python3
import asyncio
import logging
import ssl
import sys
from os import environ, execv
from typing import List

from asyncio_paho import AsyncioPahoClient

import pjrpc
from pjrpc.server.integration.aio_paho import Executor

methods = pjrpc.server.MethodRegistry()


@methods.add
def get_methods() -> List[str]:
    return ["sum", "tick"]


@methods.add
def sum(a: int, b: int) -> int:
    """RPC method implementing calls to sum(1, 2) -> 3"""
    return a + b


@methods.add
def tick() -> None:
    """RPC method implementing notification 'tick'"""
    print("examples/aio_pika_server.py: received tick")


async def setup_mqtt_server_connection() -> Executor:
    rpc = Executor(debug_messages=True)
    rpc.client = AsyncioPahoClient(client_id=environ.get("DEV_MQTT_CLIENTID", ""))

    username = environ.get("DEV_MQTT_USER", "")
    password = environ.get("DEV_MQTT_PASSWORD", "")
    rpc.client.username_pw_set(username, password)

    request_topic = environ.get("MQTT_RPC_REQUEST_TOPIC", "")
    response_topic = environ.get("MQTT_RPC_RESPONSE_TOPIC", "")
    rpc.topics(request_topic=request_topic, response_topic=response_topic)
    return rpc


async def server() -> None:
    handle_requests = True
    rpc = await setup_mqtt_server_connection()

    @methods.add
    def schedule_restart() -> None:
        """Schedule a restart, allows for an ack and response delivery"""
        loop = asyncio.get_event_loop()
        loop.call_later(0.01, execv(__file__, sys.argv))

    @methods.add
    def schedule_shutdown() -> None:
        """Schedule a shutdown, allows for an orderly disconnect from the server"""
        nonlocal handle_requests
        handle_requests = False
        loop = asyncio.get_event_loop()
        loop.call_later(0.1, loop.stop)

    rpc.dispatcher.add_methods(methods)
    broker = environ.get("MQTT_SSL_BROKER")
    assert broker
    # Connect to broker using mqtts (mqtt+tls) on port 8883:
    rpc.client.tls_set(cert_reqs=ssl.CERT_NONE)
    # To disable verification of the server hostname in the server certificate:
    # rpc.client.tls_insecure_set(True)
    await rpc.connect(broker, port=8883)
    while handle_requests:
        await rpc.handle_messages()
    await rpc.disconnect()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    asyncio.run(server())
