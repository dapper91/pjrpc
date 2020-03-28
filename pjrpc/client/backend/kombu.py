import logging
from typing import Any, Dict, Optional

import kombu.mixins

import pjrpc
from pjrpc.common import UNSET
from pjrpc.client import AbstractClient

logger = logging.getLogger(__package__)


class Client(AbstractClient):
    """
    `kombu <https://aio-pika.readthedocs.io/en/latest/>`_ based JSON-RPC client.
    Note: the client is not thread-safe.

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
        broker_url: str,
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
        self._connection = kombu.Connection(broker_url, **(conn_args or {}))
        self._routing_key = routing_key or queue_name
        self._result_queue = None
        self._result_queue_args = result_queue_args
        self._exchange = None
        self._exchange_args = exchange_args

        if exchange_name:
            self._exchange = kombu.Exchange(exchange_name,  **(exchange_args or {}))
        if result_queue_name:
            self._result_queue = kombu.Queue(result_queue_name, **(result_queue_args or {}))

    def close(self) -> None:
        """
        Closes the current broker connection.
        """

        self._connection.close()

    def _request(self, request_text: str, is_notification: bool = False, **kwargs: Any) -> Optional[str]:
        """
        Sends a JSON-RPC request.

        :param request_text: request text
        :param is_notification: is the request a notification
        :param kwargs: publish additional arguments
        :returns: response text
        """

        if is_notification:
            with kombu.Producer(self._connection) as producer:
                producer.publish(
                    request_text,
                    exchange=self._exchange or '',
                    routing_key=self._routing_key,
                    content_type='application/json',
                    **kwargs,
                )
                return None

        request_id = kombu.uuid()
        result_queue = self._result_queue or kombu.Queue(
            exclusive=True, name=request_id, **(self._result_queue_args or {})
        )

        with kombu.Producer(self._connection) as producer:
            producer.publish(
                request_text,
                exchange=self._exchange or '',
                routing_key=self._routing_key,
                reply_to=result_queue.name,
                correlation_id=request_id,
                content_type='application/json',
                **kwargs,
            )

        response = UNSET

        def on_response(message: kombu.Message) -> None:
            nonlocal response

            try:
                if message.properties.get('correlation_id') != request_id:
                    logger.warning("unexpected message received: %r", message)
                    return

                if message.content_type != 'application/json':
                    raise pjrpc.exc.DeserializationError(f"unexpected response content type: {message.content_type}")
                else:
                    response = message.body
            except Exception as e:
                response = e

        with kombu.Consumer(self._connection, on_message=on_response, queues=result_queue, no_ack=True):
            while response is UNSET:
                self._connection.drain_events(timeout=kwargs.get('timeout', None))

        if isinstance(response, Exception):
            raise response

        return response
