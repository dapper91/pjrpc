"""Based on pjrpc/client/backend/aio_pika.py (but much simpler due to MQTT),
this module implements the JSON-RPC backend for JSON-RPC over MQTT brokers"""
import asyncio
import logging
from typing import Any, List, Optional

import paho.mqtt.client as paho  # type: ignore
from asyncio_paho import AsyncioPahoClient  # type: ignore

from pjrpc.client import AbstractAsyncClient

debug = logging.getLogger(__package__).debug


class Client(AbstractAsyncClient):
    _client: AsyncioPahoClient
    """
    JSON-RPC client based on `asyncio-mqtt <https://github.com/sbtinstruments/asyncio-mqtt/>`_

    :param debug: Whether to enable debugging for the paho mqtt backend
    :param kwargs: parameters to be passed to :py:class:`pjrpc.client.AbstractClient`
    """

    def __init__(self, **kwargs: Any):
        self._debug = kwargs.pop("debug", False)
        super().__init__(**kwargs)

    def topics(
        self,
        request_topic: str,
        response_topic: str,
        **kwargs: Any,
    ) -> None:
        """Defines the topics for publishing and subscribing at the broker."""
        self._request_topic = request_topic
        self._response_topic = response_topic

        subscribe_result: tuple[int, int] = (-1, -1)
        self._subscribed_future: asyncio.Future[str] = asyncio.Future()
        self._rpc_futures: List[asyncio.Future[str]] = []
        if "debug" in kwargs:
            self._debug = kwargs.pop("debug")

        def on_connect(
            client: paho.Client,
            userdata: Any,
            flags_dict: dict[str, Any],
            result: int,
        ) -> None:
            # pylint: disable=unused-argument
            nonlocal subscribe_result
            if self._debug:
                debug(f"aio_paho: Connected, subscribe to: {self._response_topic}")
            subscribe_result = client.subscribe(self._response_topic)
            assert subscribe_result[0] == paho.MQTT_ERR_SUCCESS
            if self._debug:
                debug(f"aio_paho: Subscribed to {self._response_topic}")

        def on_subscribe(
            client: paho.Client,
            userdata: Any,
            mid: int,
            granted_qos: tuple[int, ...],
        ) -> None:
            # pylint: disable=unused-argument
            if self._debug:
                debug(f"aio_paho: Subscribed to: {self._response_topic}")
            nonlocal subscribe_result
            assert mid == subscribe_result[1]
            self._subscribed_future.set_result("")

        def on_message(client: paho.Client, userdt: Any, msg: paho.MQTTMessage) -> None:
            # pylint: disable=unused-argument
            if self._debug:
                debug(f"aio_paho: Received from {msg.topic}: {str(msg.payload)}")
            future = self._rpc_futures[-1]
            future.set_result(msg.payload.decode())

        def on_connect_fail(client: paho.Client, userdata: Any) -> None:
            # pylint: disable=unused-argument
            debug("aio_paho: Connect failed")

        def on_log(client: paho.Client, userdata: Any, level: int, buf: Any) -> None:
            # pylint: disable=unused-argument
            debug(f"aio_paho: {buf}")

        self._client.on_connect = on_connect
        self._client.on_connect_fail = on_connect_fail
        self._client.on_subscribe = on_subscribe
        self._client.on_message = on_message
        if self._debug:
            self._client.on_log = on_log

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
        self._client.connect_async(
            host,
            port,
            keepalive,
            bind_address,
            bind_port,
            clean_start,
            properties,
        )
        await self._subscribed_future

    async def close(self) -> None:
        """Close the current connection to the MQTT broker and send exceptions."""
        await self._client.close()
        for future in self._rpc_futures:
            if future.done():
                continue
            future.set_exception(asyncio.CancelledError)

    async def _request(
        self,
        request_text: str,
        is_notification: bool = False,
        **kwargs: Any,
    ) -> Optional[str]:
        """Publish an RPC request to the MQTT topic and return the received result"""
        if not is_notification:
            future: asyncio.Future[str] = asyncio.Future()
            self._rpc_futures.append(future)
        if self._debug:
            debug(f"aio_paho: {self._request_topic}: publish '{request_text}'")
        self._client.publish(self._request_topic, request_text.encode())
        if is_notification:
            return None
        received = await future
        self._rpc_futures.pop()
        return received
