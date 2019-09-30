"""
kombu JSON-RPC server integration.
"""

import logging

import kombu.mixins

import pjrpc

logger = logging.getLogger(__package__)


class Executor(kombu.mixins.ConsumerProducerMixin):
    """
    `kombu <http://kombu.readthedocs.org/>`_ based JSON-RPC server.

    :param broker_url: broker connection url
    :param queue_name: requests queue name
    :param conn_args: additional connection arguments
    :param queue_args: queue arguments
    :param publish_args: message publish additional arguments
    :param prefetch_count: worker prefetch count
    :param kwargs: dispatcher additional arguments
    """

    def __init__(
        self, broker_url, queue_name, conn_args=None, queue_args=None, publish_args=None, prefetch_count=0, **kwargs
    ):
        self.connection = kombu.Connection(broker_url, **(conn_args or {}))

        self._rpc_queue = kombu.Queue(queue_name, **(queue_args or {}))
        self._prefetch_count = prefetch_count
        self._publish_args = publish_args

        self._dispatcher = pjrpc.server.Dispatcher(**kwargs)

    @property
    def dispatcher(self):
        """
        JSON-RPC method dispatcher.
        """

        return self._dispatcher

    def get_consumers(self, Consumer, channel):
        return [Consumer(
            queues=[self._rpc_queue],
            on_message=self._rpc_handle,
            accept={'application/json'},
            prefetch_count=self._prefetch_count,
        )]

    def _rpc_handle(self, message):
        """
        Handles JSON-RPC request.

        :param message: kombu message :py:class:`kombu.message.Message`
        """

        try:
            reply_to = message.properties.get('reply_to')
            response_text = self._dispatcher.dispatch(message.body, context=message)

            if response_text is not None:
                if reply_to is None:
                    logger.warning("property 'reply_to' is missing")
                else:
                    self.producer.publish(
                        response_text,
                        routing_key=reply_to,
                        correlation_id=message.properties.get('correlation_id'),
                        content_type='application/json',
                        **(self._publish_args or {})
                    )

            message.ack()

        except Exception as e:
            logger.exception("jsonrpc request handling error: %s", e)
