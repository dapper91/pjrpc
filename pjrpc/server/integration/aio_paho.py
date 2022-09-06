"""Server side JSON-RPC over MQTT: Implements an RPC responder as an MQTT cliet"""
import asyncio
import logging
from typing import Any, List

import paho.mqtt.client as paho  # type: ignore
from asyncio_paho import AsyncioPahoClient  # type: ignore

import pjrpc.server

debug = logging.getLogger(__package__).debug


class Executor:
    """
    JSON-RPC server based on `asyncio-mqtt <https://github.com/sbtinstruments/asyncio-mqtt/>`_

    :param debug_messages: Whether to log MQTT messages with loglevel logging.DEBUG
    :param kwargs: dispatcher additional arguments and bool debug_messages
    """

    client: AsyncioPahoClient

    def __init__(self, **kwargs: Any):
        self._debug_messages = kwargs.pop("debug_messages", False)
        self._dispatcher = pjrpc.server.AsyncDispatcher(**kwargs)
        self._connected = False

    @property
    def dispatcher(self) -> pjrpc.server.AsyncDispatcher:
        """JSON-RPC method dispatcher."""
        return self._dispatcher

    def topics(
        self,
        request_topic: str,
        response_topic: str,
    ) -> None:
        """Defines the topics for publishing and subscribing at the broker."""
        self._response_topic = response_topic

        subscribe_result: tuple[int, int] = (-1, -1)
        self._subscribed_event = asyncio.Event()
        self._received_event = asyncio.Event()
        self._messages: List[paho.MQTTMessage] = []

        def on_connect(
            client: paho.Client,
            userdata: Any,
            flags_dict: dict[str, Any],
            result: int,
        ) -> None:
            # pylint: disable=unused-argument
            nonlocal subscribe_result
            debug(f"aio_paho: Connected, subscribe to: {request_topic}")
            subscribe_result = client.subscribe(request_topic)
            assert subscribe_result[0] == paho.MQTT_ERR_SUCCESS
            debug(f"aio_paho: Subscribing to {request_topic}")

        def on_subscribe(
            client: paho.Client,
            userdata: Any,
            mid: int,
            granted_qos: tuple[int, ...],
        ) -> None:
            # pylint: disable=unused-argument
            debug(f"aio_paho: Subscribed to: {request_topic}")
            nonlocal subscribe_result
            assert mid == subscribe_result[1]
            self._subscribed_event.set()

        def on_message(client: paho.Client, ud: Any, message: paho.MQTTMessage) -> None:
            # pylint: disable=unused-argument
            self._messages.append(message)
            self._received_event.set()

        def on_connect_fail(client: paho.Client, userdata: Any) -> None:
            # pylint: disable=unused-argument
            debug("aio_paho: Connect failed")

        def on_disconnect(client: paho.Client, userdata: Any, status: Any) -> None:
            # pylint: disable=unused-argument
            if not self._connected:
                return
            debug("aio_paho: disconnect by server: server shutdown or concurrent login")

        def on_log(client: paho.Client, userdata: Any, level: int, buf: Any) -> None:
            # pylint: disable=unused-argument
            debug(f"aio_paho: {buf}")

        self.client.on_connect = on_connect
        self.client.on_disconnect = on_disconnect
        self.client.on_connect_fail = on_connect_fail
        self.client.on_subscribe = on_subscribe
        self.client.on_message = on_message
        if self._debug_messages:
            self.client.on_log = on_log

    async def connect(
        self,
        host: str,
        port: int = 1883,
        keepalive: int = 60,
        bind_address: str = "",
        bind_port: int = 0,
        clean_start: bool | int = paho.MQTT_CLEAN_START_FIRST_ONLY,
        properties: paho.Properties | None = None,
    ) -> None:
        """Opens a connection to the broker."""
        self.client.connect_async(
            host, port, keepalive, bind_address, bind_port, clean_start, properties,
        )
        await self._subscribed_event.wait()
        self._connected = True

    async def handle_message(self, message: paho.MQTTMessage) -> None:
        response = await self._dispatcher.dispatch(message.payload.decode(), message)
        if response is not None:
            self.client.publish(self._response_topic, response.encode())

    async def handle_messages(self) -> None:
        await self._received_event.wait()
        self._received_event.clear()
        while self._connected and self._messages:
            await self.handle_message(self._messages.pop())

    async def disconnect(self) -> None:
        """Close the current connection"""
        self._connected = False
        self.client.disconnect()
        self._messages = []
        self._subscribed_event.clear()
        self._received_event.clear()
