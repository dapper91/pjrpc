import asyncio
import json
import logging
import typing
import uuid
from typing import Any, Callable, Generator, Iterable, Mapping, Optional, TypedDict

import aio_pika
from aio_pika.abc import AbstractIncomingMessage
from yarl import URL

import pjrpc
from pjrpc.client import AbstractAsyncClient, AsyncMiddleware
from pjrpc.common import AbstractRequest, AbstractResponse, BatchRequest, BatchResponse, JSONEncoder, JsonRpcError
from pjrpc.common import Request, Response, generators
from pjrpc.common.typedefs import JsonRpcRequestIdT

logger = logging.getLogger(__package__)


class ExchangeArgs(TypedDict, total=False):
    type: aio_pika.ExchangeType
    durable: bool
    auto_delete: bool
    internal: bool
    passive: bool
    arguments: aio_pika.abc.Arguments
    timeout: aio_pika.abc.TimeoutType


class QueueArgs(TypedDict, total=False):
    durable: bool
    passive: bool
    auto_delete: bool
    arguments: aio_pika.abc.Arguments
    timeout: aio_pika.abc.TimeoutType


class RequestArgs(TypedDict, total=False):
    headers: aio_pika.abc.HeadersType
    delivery_mode: aio_pika.abc.DeliveryMode
    priority: int
    expiration: aio_pika.abc.DateType
    message_id: str
    timestamp: aio_pika.abc.DateType
    type: str
    user_id: str
    app_id: str


class Client(AbstractAsyncClient):
    """
    `aio_pika <https://docs.aio-pika.com/>`_ based JSON-RPC client.

    :param broker_url: broker connection url
    :param connection: broker connection
    :param exchange_name: exchange to publish requests to. If ``None`` default exchange is used
    :param exchange_args: exchange arguments
    :param routing_key: reply message routing key. If ``None`` queue name is used
    :param result_queue_name: result queue name. If ``None`` random exclusive queue is declared for each request
    :param id_gen_impl: identifier generator
    :param error_cls: JSON-RPC error base class
    :param json_loader: json loader
    :param json_dumper: json dumper
    :param json_encoder: json encoder
    :param json_decoder: json decoder
    """

    def __init__(
        self,
        broker_url: Optional[URL] = None,
        *,
        connection: Optional[aio_pika.abc.AbstractConnection] = None,
        exchange_name: str = "",
        routing_key: str,
        exchange_args: Optional[ExchangeArgs] = None,
        result_queue_name: Optional[str] = None,
        result_queue_args: Optional[QueueArgs] = None,
        id_gen_impl: Callable[..., Generator[JsonRpcRequestIdT, None, None]] = generators.sequential,
        error_cls: type[JsonRpcError] = JsonRpcError,
        json_loader: Callable[..., Any] = json.loads,
        json_dumper: Callable[..., str] = json.dumps,
        json_encoder: type[JSONEncoder] = JSONEncoder,
        json_decoder: Optional[json.JSONDecoder] = None,
        middlewares: Iterable[AsyncMiddleware] = (),
    ):
        assert broker_url or connection, "broker_url or connection must be provided"

        super().__init__(
            id_gen_impl=id_gen_impl,
            error_cls=error_cls,
            json_loader=json_loader,
            json_dumper=json_dumper,
            json_encoder=json_encoder,
            json_decoder=json_decoder,
            middlewares=middlewares,
        )

        if connection is not None:
            self._connection = connection
            self._is_connection_owned = False
        else:
            assert broker_url
            self._connection = aio_pika.connection.Connection(broker_url)
            self._is_connection_owned = True

        self._channel: Optional[aio_pika.abc.AbstractChannel] = None

        self._routing_key = routing_key
        self._exchange_name = exchange_name
        self._exchange_args = exchange_args or {}
        self._exchange: Optional[aio_pika.abc.AbstractExchange] = None

        self._result_queue_name = result_queue_name
        self._result_queue_args: QueueArgs = result_queue_args or {}
        self._result_queue: Optional[aio_pika.abc.AbstractQueue] = None
        self._consumer_tag: Optional[str] = None

        self._futures: dict[str, asyncio.Future[str]] = {}

    async def __aenter__(self) -> 'Client':
        await self.connect()
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    async def connect(self) -> None:
        """
        Opens a connection to the broker.
        """

        if self._is_connection_owned:
            await self._connection.connect()

        self._channel = channel = await self._connection.channel()

        if self._exchange_name:
            self._exchange = await channel.declare_exchange(self._exchange_name, **self._exchange_args)

        if self._result_queue_name:
            self._result_queue = await channel.declare_queue(self._result_queue_name, **self._result_queue_args)
            self._consumer_tag = await self._result_queue.consume(self._on_result_message, no_ack=True)

    async def close(self) -> None:
        """
        Closes current broker connection.
        """

        if self._consumer_tag and self._result_queue:
            await self._result_queue.cancel(self._consumer_tag)
            self._consumer_tag = None

        for future in self._futures.values():
            if future.done():
                continue

            future.set_exception(asyncio.CancelledError)

        if self._channel:
            await self._channel.close()
            self._channel = None

        if self._connection and self._is_connection_owned:
            await self._connection.close()

    @typing.overload
    async def send(self, request: Request, **kwargs: Any) -> Optional[Response]:
        ...

    @typing.overload
    async def send(self, request: BatchRequest, **kwargs: Any) -> Optional[BatchResponse]:
        ...

    async def send(self, request: AbstractRequest, **kwargs: Any) -> Optional[AbstractResponse]:
        """
        Sends a JSON-RPC request.

        :param request: request instance
        :param kwargs: additional client request argument
        :returns: response instance or None if the request is a notification
        """

        return await self._send(request, kwargs)

    async def _on_result_message(self, message: AbstractIncomingMessage) -> None:
        if not (correlation_id := message.correlation_id):
            logger.info("message correlation id is missing", message.correlation_id)
            return

        future = self._futures.pop(correlation_id, None)

        if future is None:
            logger.warning("unexpected or outdated message received: %r", message)
            return

        if message.content_type not in self._response_content_types:
            future.set_exception(
                pjrpc.exc.DeserializationError(f"unexpected response content type: {message.content_type}"),
            )
        else:
            future.set_result(message.body.decode(message.content_encoding or 'utf8'))

    async def _request(
        self,
        request_text: str,
        is_notification: bool,
        request_kwargs: Mapping[str, Any],
    ) -> Optional[str]:
        assert self._channel, "server is not started"

        request_kwargs = typing.cast(RequestArgs, request_kwargs)

        if is_notification:
            message = aio_pika.message.Message(
                body=request_text.encode(),
                content_encoding='utf8',
                content_type=self._request_content_type,
                **request_kwargs,
            )
            exchange = self._exchange or self._channel.default_exchange
            await exchange.publish(message, routing_key=self._routing_key)
            return None

        request_id = str(uuid.uuid4())

        if not self._result_queue:
            result_queue = await self._channel.declare_queue(request_id, exclusive=True, **self._result_queue_args)
            await result_queue.consume(self._on_result_message, no_ack=True)
        else:
            result_queue = self._result_queue

        message = aio_pika.message.Message(
            body=request_text.encode(),
            correlation_id=request_id,
            reply_to=result_queue.name,
            content_encoding='utf8',
            content_type=self._request_content_type,
            **request_kwargs,
        )

        future: asyncio.Future[str] = asyncio.Future()
        self._futures[request_id] = future

        try:
            exchange = self._exchange or self._channel.default_exchange
            await exchange.publish(message, routing_key=self._routing_key)
            return await future
        finally:
            self._futures.pop(request_id, None)
