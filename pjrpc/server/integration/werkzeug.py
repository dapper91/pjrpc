from typing import Any, Dict, Callable

import werkzeug
from werkzeug import exceptions

import pjrpc


class JsonRPC:
    """
    `werkzeug <https://werkzeug.palletsprojects.com/en/0.16.x/>`_ server JSON-RPC integration.

    :param path: JSON-RPC handler base path
    :param kwargs: arguments to be passed to the dispatcher :py:class:`pjrpc.server.Dispatcher`
    """

    def __init__(self, path: str = '', **kwargs: Any):
        self._path = path
        self._dispatcher = pjrpc.server.Dispatcher(**kwargs)

    def __call__(self, environ: Dict[str, Any], start_response: Callable):
        return self.wsgi_app(environ, start_response)

    def wsgi_app(self, environ: Dict[str, Any], start_response: Callable):
        environ['app'] = self
        request = werkzeug.Request(environ)
        response = self._rpc_handle(request)
        return response(environ, start_response)

    @property
    def dispatcher(self) -> pjrpc.server.Dispatcher:
        """
        JSON-RPC method dispatcher.
        """

        return self._dispatcher

    def _rpc_handle(self, request: werkzeug.Request) -> werkzeug.Response:
        """
        Handles JSON-RPC request.

        :returns: werkzeug response
        """

        if request.content_type != 'application/json':
            raise exceptions.UnsupportedMediaType()

        try:
            request_text = request.get_data(as_text=True)
        except UnicodeDecodeError as e:
            raise exceptions.BadRequest() from e

        response_text = self._dispatcher.dispatch(request_text, context=request)
        if response_text is None:
            return werkzeug.Response()
        else:
            return werkzeug.Response(response_text, mimetype='application/json')
