import logging
from types import SimpleNamespace
from typing import Union

from pjrpc import BatchRequest, Request, Response

client_logger = logging.getLogger(__package__)


class Tracer:
    """
    JSON-RPC client tracer.
    """

    def on_request_begin(self, trace_context: SimpleNamespace, request: Request) -> None:
        """
        Handler called before JSON-RPC request begins.

        :param trace_context: request trace context
        :param request: JSON-RPC request
        """

    def on_request_end(self, trace_context: SimpleNamespace, request: Request, response: Response) -> None:
        """
        Handler called after JSON-RPC request ends.

        :param trace_context: request trace context
        :param request: JSON-RPC request
        :param response: JSON-RPC response
        """

    def on_error(
        self, trace_context: SimpleNamespace, request: Union[Request, BatchRequest], error: BaseException,
    ) -> None:
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

    def __init__(self, logger: logging.Logger = client_logger, level: int = logging.DEBUG):
        self._logger = logger
        self._level = level

    def on_request_begin(self, trace_context: SimpleNamespace, request: Request) -> None:
        self._logger.log(self._level, "sending request: %r", request)

    def on_request_end(self, trace_context: SimpleNamespace, request: Request, response: Response) -> None:
        self._logger.log(self._level, "received response: %r", response)

    def on_error(
        self, trace_context: SimpleNamespace, request: Union[Request, BatchRequest], error: BaseException,
    ) -> None:
        self._logger.log(self._level, "request '%s' sending error: %r", request, error)
