import asyncio
import logging
import uuid

import aio_pika

from pjrpc.client import AbstractAsyncClient

logger = logging.getLogger(__package__)


class Client(AbstractAsyncClient):
    """
    `aio_pika <http://kombu.readthedocs.org/>`_ based JSON-RPC client.

    :param broker_url: broker connection url
    :param conn_args: broker connection arguments.
    :param queue_name: queue name to publish requests to
    :param exchange_name: exchange to publish requests to. If ``None`` default exchange is used
    :param routing_key: reply message routing key. If ``None`` queue name is used
    :param result_queue_name: result queue name. If ``None`` random exclusive queue is declared for each request
    :param conn_args: additional connection arguments
    :param kwargs: parameters to be passed to :py:class:`pjrpc.client.AbstractClient`
    """

    def __init__(
        self,
        broker_url,
        queue_name=None,
        conn_args=None,
        exchange_name=None,
        exchange_args=None,
        routing_key=None,
        result_queue_name=None,
        result_queue_args=None,
        **kwargs,
    ):
        assert queue_name or routing_key, "queue_name or routing_key must be provided"

        super().__init__(**kwargs)
        self._connection = aio_pika.connection.Connection(broker_url, **(conn_args or {}))
        self._channel = None

        self._exchange_name = exchange_name
        self._exchange_args = exchange_args
        self._exchange = None

        self._routing_key = routing_key or queue_name
        self._result_queue_name = result_queue_name
        self._result_queue_args = result_queue_args
        self._result_queue = None
        self._consumer_tag = None

        self._futures = {}

    async def connect(self):
        """
        Opens a connection to the broker.
        """

        await self._connection.connect()
        self._channel = await self._connection.channel()

        if self._exchange_name:
            self._exchange = aio_pika.Exchange(
                self._connection, self._channel, self._exchange_name, **(self._exchange_args or {})
            )
            await self._exchange.declare()

        if self._result_queue_name:
            self._result_queue = aio_pika.Queue(
                self._connection, self._channel, self._result_queue_name, **(self._result_queue_args or {})
            )
            await self._result_queue.declare()
            self._consumer_tag = await self._result_queue.consume(self._on_result_message, no_ack=True)

    async def close(self):
        """
        Closes current broker connection.
        """

        await self._result_queue.cancel(self._consumer_tag)
        await self._channel.close()
        await self._connection.close()
        self._consumer_tag = None

        for future in self._futures.values():
            if future.done():
                continue

            future.set_exception(asyncio.CancelledError)

    async def _on_result_message(self, message):
        correlation_id = message.correlation_id
        future = self._futures.pop(correlation_id, None)

        if future is None:
            logger.warning("unexpected message: %r", message)
            return

        future.set_result(message.body)

    async def _request(self, data, **kwargs):
        request_id = str(uuid.uuid4())

        async with self._connection.channel() as channel:
            if not self._result_queue:
                result_queue = await channel.declare_queue(
                    request_id, exclusive=True, **(self._result_queue_args or {})
                )
                await result_queue.consume(self._on_result_message, no_ack=True)
            else:
                result_queue = self._result_queue

            message = aio_pika.message.Message(
                body=data.encode(),
                correlation_id=request_id,
                reply_to=result_queue.name,
                content_encoding='utf8',
                content_type='application/json',
                **kwargs,
            )

            try:
                self._futures[request_id] = future = asyncio.Future()

                exchange = self._exchange or channel.default_exchange
                await exchange.publish(message, routing_key=self._routing_key)
                return await future
            finally:
                self._futures.pop(request_id, None)
