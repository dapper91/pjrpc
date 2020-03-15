import logging

from .client import logger as client_logger


class Tracer:
    """
    JSON-RPC client tracer.
    """

    def on_request_begin(self, trace_context, request):
        """
        Handler called before JSON-RPC request begins.

        :param trace_context: request trace context
        :param request: JSON-RPC request
        """

    def on_request_end(self, trace_context, request, response):
        """
        Handler called after JSON-RPC request ends.

        :param trace_context: request trace context
        :param request: JSON-RPC request
        :param response: JSON-RPC response
        """

    def on_error(self, trace_context, request, error):
        """
        Handler called when JSON-RPC request failed.

        :param trace_context: request trace context
        :param request: JSON-RPC request
        :param error: raised exception
        """


class LoggingTracer(Tracer):
    """
    JSON-RPC client logging tracer.
    """

    def __init__(self, logger=client_logger, level=logging.DEBUG):
        self._logger = logger
        self._level = level

    def on_request_begin(self, trace_context, request):
        self._logger.log(self._level, "sending request: %r", request)

    def on_request_end(self, trace_context, request, response):
        self._logger.log(self._level, "received response: %r", response)

    def on_error(self, trace_context, request, error):
        self._logger.log(self._level, "request '%s' sending error: %r", request, error)
