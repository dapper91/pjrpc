import logging

import kombu.mixins

from pjrpc.common import UNSET
from pjrpc.client import AbstractClient

logger = logging.getLogger(__package__)


class Client(AbstractClient):
    """
    `kombu <https://aio-pika.readthedocs.io/en/latest/>`_ based JSON-RPC client.

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
        routing_key=None,
        result_queue_name=None,
        result_queue_args=None,
        **kwargs,
    ):
        assert queue_name or routing_key, "queue_name or routing_key must be provided"

        super().__init__(**kwargs)
        self.connection = kombu.Connection(broker_url, **(conn_args or {}))
        self._routing_key = routing_key or queue_name
        self._result_queue_args = result_queue_args
        self._result_queue = None
        self._exchange = None

        if exchange_name:
            self._exchange = kombu.Exchange(exchange_name)
        if result_queue_name:
            self._result_queue = kombu.Queue(result_queue_name, **(result_queue_args or {}))

    def close(self):
        """
        Closes the current broker connection.
        """

        self.connection.close()

    def _request(self, data, **kwargs):
        """
        Sends a JSON-RPC request.

        :param data: request text
        :param kwargs: publish additional arguments
        :returns: response text
        """

        request_id = kombu.uuid()
        result_queue = self._result_queue or kombu.Queue(
            exclusive=True, name=request_id, **(self._result_queue_args or {})
        )

        with kombu.Producer(self.connection) as producer:
            producer.publish(
                data,
                exchange=self._exchange or '',
                routing_key=self._routing_key,
                reply_to=result_queue.name,
                correlation_id=request_id,
                content_type='application/json',
                **kwargs,
            )

        response = UNSET

        def on_response(message):
            nonlocal response

            if message.properties.get('correlation_id') == request_id:
                response = message.body
            else:
                logger.warning("unexpected message: %r", message)

        with kombu.Consumer(self.connection, on_message=on_response, queues=result_queue, no_ack=True):
            while response is UNSET:
                self.connection.drain_events(timeout=kwargs.get('timeout', None))

        return response
