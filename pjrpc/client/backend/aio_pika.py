import asyncio
import logging
import uuid
from typing import Any, Dict, Optional, cast

import aio_pika
from aio_pika.abc import AbstractIncomingMessage
from yarl import URL

import pjrpc
from pjrpc.client import AbstractAsyncClient

logger = logging.getLogger(__package__)


class Client(AbstractAsyncClient):
    """
    `aio_pika <http://kombu.readthedocs.org/>`_ based JSON-RPC client.

    :param broker_url: broker connection url
    :param conn_args: broker connection arguments.
    :param queue_name: queue name to publish requests to
    :param exchange_name: exchange to publish requests to. If ``None`` default exchange is used
    :param exchange_args: exchange arguments
    :param routing_key: reply message routing key. If ``None`` queue name is used
    :param result_queue_name: result queue name. If ``None`` random exclusive queue is declared for each request
    :param conn_args: additional connection arguments
    :param kwargs: parameters to be passed to :py:class:`pjrpc.client.AbstractClient`
    """

    def __init__(
        self,
        broker_url: URL,
        queue_name: Optional[str] = None,
        conn_args: Optional[Dict[str, Any]] = None,
        exchange_name: Optional[str] = None,
        exchange_args: Optional[Dict[str, Any]] = None,
        routing_key: Optional[str] = None,
        result_queue_name: Optional[str] = None,
        result_queue_args: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ):
        assert queue_name or routing_key, "queue_name or routing_key must be provided"

        super().__init__(**kwargs)
        self._connection = aio_pika.connection.Connection(broker_url, **(conn_args or {}))
        self._channel: Optional[aio_pika.abc.AbstractChannel] = None

        self._exchange_name = exchange_name
        self._exchange_args = exchange_args
        self._exchange: Optional[aio_pika.abc.AbstractExchange] = None

        self._routing_key = cast(str, routing_key or queue_name)
        self._result_queue_name = result_queue_name
        self._result_queue_args = result_queue_args
        self._result_queue: Optional[aio_pika.abc.AbstractQueue] = None
        self._consumer_tag: Optional[str] = None

        self._futures: Dict[str, asyncio.Future[str]] = {}

    async def connect(self) -> None:
        """
        Opens a connection to the broker.
        """

        await self._connection.connect()
        self._channel = channel = await self._connection.channel()

        if self._exchange_name:
            self._exchange = await channel.declare_exchange(self._exchange_name, **(self._exchange_args or {}))

        if self._result_queue_name:
            assert channel
            self._result_queue = await channel.declare_queue(
                self._result_queue_name, **(self._result_queue_args or {}),
            )
            self._consumer_tag = await self._result_queue.consume(self._on_result_message, no_ack=True)

    async def close(self) -> None:
        """
        Closes current broker connection.
        """

        if self._consumer_tag and self._result_queue:
            await self._result_queue.cancel(self._consumer_tag)
            self._consumer_tag = None

        if self._channel:
            await self._channel.close()
            self._channel = None
        if self._connection:
            await self._connection.close()
            self._connection = None

        for future in self._futures.values():
            if future.done():
                continue

            future.set_exception(asyncio.CancelledError)

    async def _on_result_message(self, message: AbstractIncomingMessage) -> None:
        correlation_id = message.correlation_id
        assert correlation_id
        future = self._futures.pop(correlation_id, None)

        if future is None:
            logger.warning("unexpected or outdated message received: %r", message)
            return

        if message.content_type not in pjrpc.common.RESPONSE_CONTENT_TYPES:
            future.set_exception(
                pjrpc.exc.DeserializationError(f"unexpected response content type: {message.content_type}"),
            )
        else:
            future.set_result(message.body.decode(message.content_encoding or 'utf8'))

    async def _request(self, request_text: str, is_notification: bool = False, **kwargs: Any) -> Optional[str]:
        if is_notification:
            async with self._connection.channel() as channel:
                message = aio_pika.message.Message(
                    body=request_text.encode(),
                    content_encoding='utf8',
                    content_type=pjrpc.common.DEFAULT_CONTENT_TYPE,
                    **kwargs,
                )
                exchange = self._exchange or channel.default_exchange
                await exchange.publish(message, routing_key=self._routing_key)
                return None

        request_id = str(uuid.uuid4())

        async with self._connection.channel() as channel:
            if not self._result_queue:
                result_queue = await channel.declare_queue(
                    request_id, exclusive=True, **(self._result_queue_args or {}),
                )
                await result_queue.consume(self._on_result_message, no_ack=True)
            else:
                result_queue = self._result_queue

            message = aio_pika.message.Message(
                body=request_text.encode(),
                correlation_id=request_id,
                reply_to=result_queue.name,
                content_encoding='utf8',
                content_type=pjrpc.common.DEFAULT_CONTENT_TYPE,
                **kwargs,
            )

            future: asyncio.Future[str] = asyncio.Future()
            self._futures[request_id] = future

            try:
                exchange = self._exchange or channel.default_exchange
                await exchange.publish(message, routing_key=self._routing_key)
                return await future
            finally:
                self._futures.pop(request_id, None)
