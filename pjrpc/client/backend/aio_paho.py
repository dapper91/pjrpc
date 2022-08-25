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
    """
    JSON-RPC client based on `asyncio-mqtt <https://github.com/sbtinstruments/asyncio-mqtt/>`_

    :param broker: MQTT broker
    :param request_topic: MQTT topic for publishing RPC requests
    :param response_topic: MQTT topic for receiving RPC responses
    :param clientid: MQTT Client Id for connecting to the MQTT broker
    :param username: MQTT user name for connecting to the MQTT broker
    :param password: MQTT password for connecting to the MQTT broker
    :param port: Port number used by the MQTT broker(default: 1884)
    :param queue_name: queue name to publish requests to
    :param kwargs: parameters to be passed to :py:class:`pjrpc.client.AbstractClient`
    """

    def __init__(
        self,
        broker: str,
        request_topic: str,
        response_topic: str,
        clientid: Optional[str],
        username: Optional[str],
        password: Optional[str],
        port: Optional[int] = 1884,
        **kwargs: Any,
    ):
        super().__init__(**kwargs)
        self._broker = broker
        self._port = port
        self._request_topic = request_topic
        self._response_topic = response_topic
        self._clientid = clientid
        self._username = username
        self._password = password

    async def connect(self, **kwargs: Any) -> None:
        """Opens a connection to the broker.
        :param kwargs: parameters to be passed to :py:class:`asyncio_paho.AsyncioPahoClient`
        """
        subscribe_result: tuple[int, int] = (-1, -1)
        self._subscribed_future: asyncio.Future[str] = asyncio.Future()
        self._rpc_futures: List[asyncio.Future[str]] = []
        self._debug = kwargs.pop("debug", False)

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

        self._client = AsyncioPahoClient(self._clientid or "", **kwargs)
        if self._password:
            self._client.username_pw_set(self._username, self._password)
        self._client.on_connect = on_connect
        self._client.on_connect_fail = on_connect_fail
        self._client.on_subscribe = on_subscribe
        self._client.on_message = on_message
        if self._debug:
            self._client.on_log = on_log

        self._client.connect_async(self._broker)
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
