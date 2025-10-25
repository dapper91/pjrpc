import json
import logging
from typing import Any, Callable, Iterable, Optional

import aio_pika
from yarl import URL

import pjrpc.server
from pjrpc.server.dispatcher import AsyncExecutor, AsyncMiddlewareType, JSONEncoder

logger = logging.getLogger(__package__)

AioPikaDispatcher = pjrpc.server.AsyncDispatcher[aio_pika.abc.AbstractIncomingMessage]


class Executor:
    """
    `aio_pika <https://aio-pika.readthedocs.io/en/latest/>`_ based JSON-RPC server.

    :param broker_url: broker connection url
    :param request_queue_name: requests queue name
    :param response_exchange_name: response exchange name
    :param response_routing_key: response routing key
    :param prefetch_count: worker prefetch count
    """

    def __init__(
        self,
        broker_url: URL,
        request_queue_name: str,
        request_queue_args: Optional[dict[str, Any]] = None,
        response_exchange_name: Optional[str] = None,
        response_exchange_args: Optional[dict[str, Any]] = None,
        response_routing_key: Optional[str] = None,
        prefetch_count: int = 0,
        executor: Optional[AsyncExecutor] = None,
        json_loader: Callable[..., Any] = json.loads,
        json_dumper: Callable[..., str] = json.dumps,
        json_encoder: type[JSONEncoder] = JSONEncoder,
        json_decoder: Optional[type[json.JSONDecoder]] = None,
        middlewares: Iterable[AsyncMiddlewareType[aio_pika.abc.AbstractIncomingMessage]] = (),
        max_batch_size: Optional[int] = None,
    ):
        self._broker_url = broker_url
        self._request_queue_name = request_queue_name
        self._request_queue_args = request_queue_args
        self._response_exchange_name = response_exchange_name
        self._response_exchange_args = response_exchange_args
        self._response_routing_key = response_routing_key
        self._prefetch_count = prefetch_count

        self._connection = aio_pika.connection.Connection(broker_url)
        self._channel: Optional[aio_pika.abc.AbstractChannel] = None

        self._request_queue: Optional[aio_pika.abc.AbstractQueue] = None
        self._response_exchange: Optional[aio_pika.abc.AbstractExchange] = None
        self._consumer_tag: Optional[str] = None
        self._dispatcher = AioPikaDispatcher(
            executor=executor,
            json_loader=json_loader,
            json_dumper=json_dumper,
            json_encoder=json_encoder,
            json_decoder=json_decoder,
            middlewares=middlewares,
            max_batch_size=max_batch_size,
        )

    @property
    def dispatcher(self) -> AioPikaDispatcher:
        """
        JSON-RPC method dispatcher.
        """

        return self._dispatcher

    async def start(self) -> None:
        """
        Starts executor.
        """

        await self._connection.connect()
        self._channel = channel = await self._connection.channel()
        await channel.set_qos(prefetch_count=self._prefetch_count)

        self._request_queue = await channel.declare_queue(
            self._request_queue_name, **(self._request_queue_args or {}),
        )

        if self._response_exchange_name:
            self._response_exchange = await channel.declare_exchange(
                self._response_exchange_name, **(self._response_exchange_args or {}),
            )

        self._consumer_tag = await self._request_queue.consume(self._rpc_handle)

    async def shutdown(self) -> None:
        """
        Stops executor.
        """

        assert self._channel and self._request_queue and self._consumer_tag, "executor not started"

        await self._request_queue.cancel(self._consumer_tag)
        await self._channel.close()
        await self._connection.close()

    async def _rpc_handle(self, message: aio_pika.abc.AbstractIncomingMessage) -> None:
        """
        Handles JSON-RPC request.

        :param message: incoming message
        """

        async with message.process():
            try:
                if (response := await self._dispatcher.dispatch(message.body.decode(), context=message)) is not None:
                    response_text, error_codes = response

                    async with self._connection.channel() as channel:
                        exchange = self._response_exchange or channel.default_exchange
                        await exchange.publish(
                            aio_pika.Message(
                                body=response_text.encode(),
                                correlation_id=message.correlation_id,
                                content_type=pjrpc.common.DEFAULT_CONTENT_TYPE,
                            ),
                            routing_key=message.reply_to or self._response_routing_key or '',
                        )

            except Exception as e:
                logger.exception("jsonrpc request handling error: %s", e)
                raise
