import logging
import functools as ft

import aio_pika

import pjrpc

logger = logging.getLogger(__package__)


class Executor:
    """
    `aio_pika <https://aio-pika.readthedocs.io/en/latest/>`_ based JSON-RPC server.

    :param broker_url: broker connection url
    :param queue_name: requests queue name
    :param prefetch_count: worker prefetch count
    :param workers_count: number of workers
    :param kwargs: dispatcher additional arguments
    """

    class Worker:
        """
        Executor worker.
        """

        def __init__(self, connection, queue_name, handler, prefetch_count=0):
            self._connection = connection
            self._queue_name = queue_name
            self._handler = handler
            self._prefetch_count = prefetch_count

            self._channel = None
            self._queue = None
            self._consumer_tag = None

        async def start(self):
            self._channel = await self._connection.channel()
            await self._channel.set_qos(prefetch_count=self._prefetch_count)

            self._queue = await self._channel.declare_queue(self._queue_name, passive=True)
            self._consumer_tag = await self._queue.consume(ft.partial(self._handler, channel=self._channel))

        async def stop(self):
            if self._consumer_tag:
                await self._queue.cancel(self._consumer_tag)
            if self._channel:
                await self._channel.close()

    def __init__(self, broker_url, queue_name, prefetch_count=0, workers_count=1, **kwargs):
        self._broker_url = broker_url
        self._queue_name = queue_name
        self._prefetch_count = prefetch_count

        self._connection = aio_pika.connection.Connection(broker_url)
        self._workers = [
            Executor.Worker(
                self._connection, queue_name, self._rpc_handle, prefetch_count,
            ) for _ in range(workers_count)
        ]

        self._dispatcher = pjrpc.server.Dispatcher(**kwargs)

    @property
    def dispatcher(self):
        """
        JSON-RPC method dispatcher.
        """

        return self._dispatcher

    async def start(self, queue_args=None):
        """
        Starts executor.

        :param queue_args: queue arguments
        """

        await self._connection.connect()
        async with self._connection.channel() as channel:
            await channel.declare_queue(self._queue_name, **(queue_args or {}))

        for worker in self._workers:
            await worker.start()

    async def shutdown(self):
        """
        Stops executor.
        """

        for worker in self._workers:
            await worker.stop()

        await self._connection.close()

    async def _rpc_handle(self, message, channel):
        """
        Handles JSON-RPC request.

        :param channel: broker channel
        :param message: incoming message
        """

        try:
            reply_to = message.reply_to
            response_text = self._dispatcher.dispatch(message.body, context=message)

            if response_text is not None:
                if reply_to is None:
                    logger.warning("property 'reply_to' is missing")
                else:
                    await channel.default_exchange.publish(
                        aio_pika.Message(
                            body=response_text.encode(),
                            reply_to=reply_to,
                            correlation_id=message.correlation_id,
                            content_type='application/json',
                        ),
                        routing_key=reply_to
                    )

            message.ack()

        except Exception as e:
            logger.exception("jsonrpc request handling error: %s", e)
