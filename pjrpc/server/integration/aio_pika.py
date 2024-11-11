import logging
from typing import Any, Dict, Optional

import aio_pika
from yarl import URL

import pjrpc.server

logger = logging.getLogger(__package__)


class Executor:
    """
    `aio_pika <https://aio-pika.readthedocs.io/en/latest/>`_ based JSON-RPC server.

    :param broker_url: broker connection url
    :param rx_queue_name: requests queue name
    :param tx_exchange_name: response exchange name
    :param tx_routing_key: response routing key
    :param prefetch_count: worker prefetch count
    :param kwargs: dispatcher additional arguments
    """

    def __init__(
        self,
        broker_url: URL,
        rx_queue_name: str,
        tx_exchange_name: Optional[str] = None,
        tx_routing_key: Optional[str] = None,
        prefetch_count: int = 0,
        **kwargs: Any,
    ):
        self._broker_url = broker_url
        self._rx_queue_name = rx_queue_name
        self._tx_exchange_name = tx_exchange_name
        self._tx_routing_key = tx_routing_key
        self._prefetch_count = prefetch_count

        self._connection = aio_pika.connection.Connection(broker_url)
        self._channel: Optional[aio_pika.abc.AbstractChannel] = None

        self._queue: Optional[aio_pika.abc.AbstractQueue] = None
        self._exchange: Optional[aio_pika.abc.AbstractExchange] = None
        self._consumer_tag: Optional[str] = None

        self._dispatcher = pjrpc.server.AsyncDispatcher(**kwargs)

    @property
    def dispatcher(self) -> pjrpc.server.AsyncDispatcher:
        """
        JSON-RPC method dispatcher.
        """

        return self._dispatcher

    async def start(
            self,
            queue_args: Optional[Dict[str, Any]] = None,
            exchange_args: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Starts executor.

        :param queue_args: queue arguments
        :param exchange_args: exchange arguments
        """

        await self._connection.connect()
        self._channel = channel = await self._connection.channel()

        self._queue = queue = await channel.declare_queue(self._rx_queue_name, **(queue_args or {}))
        if self._tx_exchange_name:
            self._exchange = await channel.declare_exchange(self._tx_exchange_name, **(exchange_args or {}))
        await channel.set_qos(prefetch_count=self._prefetch_count)
        self._consumer_tag = await queue.consume(self._rpc_handle)

    async def shutdown(self) -> None:
        """
        Stops executor.
        """

        if self._consumer_tag and self._queue:
            await self._queue.cancel(self._consumer_tag)
        if self._channel:
            await self._channel.close()

        await self._connection.close()

    async def _rpc_handle(self, message: aio_pika.abc.AbstractIncomingMessage) -> None:
        """
        Handles JSON-RPC request.

        :param message: incoming message
        """

        try:
            reply_to = message.reply_to
            response = await self._dispatcher.dispatch(message.body.decode(), context=message)

            if response is not None:
                response_text, error_codes = response
                if self._tx_routing_key:
                    routing_key = self._tx_routing_key
                elif reply_to:
                    routing_key = reply_to
                else:
                    routing_key = ""
                    logger.warning("property 'reply_to' or 'tx_routing_key' missing")
                async with self._connection.channel() as channel:
                    exchange = self._exchange if self._exchange else channel.default_exchange
                    await exchange.publish(
                        aio_pika.Message(
                            body=response_text.encode(),
                            reply_to=reply_to,
                            correlation_id=message.correlation_id,
                            content_type=pjrpc.common.DEFAULT_CONTENT_TYPE,
                        ),
                        routing_key=routing_key,
                    )

            await message.ack()

        except Exception as e:
            logger.exception("jsonrpc request handling error: %s", e)
