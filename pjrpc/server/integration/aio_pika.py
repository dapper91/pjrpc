import logging
from typing import Any, Dict, Optional

import aio_pika

import pjrpc

logger = logging.getLogger(__package__)


class Executor:
    """
    `aio_pika <https://aio-pika.readthedocs.io/en/latest/>`_ based JSON-RPC server.

    :param broker_url: broker connection url
    :param queue_name: requests queue name
    :param prefetch_count: worker prefetch count
    :param kwargs: dispatcher additional arguments
    """

    def __init__(self, broker_url: str, queue_name: str, prefetch_count: int = 0, **kwargs: Any):
        self._broker_url = broker_url
        self._queue_name = queue_name
        self._prefetch_count = prefetch_count

        self._connection = aio_pika.connection.Connection(broker_url)
        self._channel: Optional[aio_pika.Channel] = None

        self._queue: Optional[aio_pika.Queue] = None
        self._consumer_tag: Optional[str] = None

        self._dispatcher = pjrpc.server.AsyncDispatcher(**kwargs)

    @property
    def dispatcher(self) -> pjrpc.server.AsyncDispatcher:
        """
        JSON-RPC method dispatcher.
        """

        return self._dispatcher

    async def start(self, queue_args: Optional[Dict[str, Any]] = None) -> None:
        """
        Starts executor.

        :param queue_args: queue arguments
        """

        await self._connection.connect()
        self._channel = await self._connection.channel()

        self._queue = await self._channel.declare_queue(self._queue_name, **(queue_args or {}))
        await self._channel.set_qos(prefetch_count=self._prefetch_count)
        self._consumer_tag = await self._queue.consume(self._rpc_handle)

    async def shutdown(self) -> None:
        """
        Stops executor.
        """

        if self._consumer_tag:
            await self._queue.cancel(self._consumer_tag)
        if self._channel:
            await self._channel.close()

        await self._connection.close()

    async def _rpc_handle(self, message: aio_pika.IncomingMessage) -> None:
        """
        Handles JSON-RPC request.

        :param message: incoming message
        """

        try:
            reply_to = message.reply_to
            response_text = await self._dispatcher.dispatch(message.body, context=message)

            if response_text is not None:
                if reply_to is None:
                    logger.warning("property 'reply_to' is missing")
                else:
                    async with self._connection.channel() as channel:
                        await channel.default_exchange.publish(
                            aio_pika.Message(
                                body=response_text.encode(),
                                reply_to=reply_to,
                                correlation_id=message.correlation_id,
                                content_type='application/json',
                            ),
                            routing_key=reply_to,
                        )

            message.ack()

        except Exception as e:
            logger.exception("jsonrpc request handling error: %s", e)
