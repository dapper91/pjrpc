"""
Flask JSON-RPC extension.
"""

from typing import Any

import flask
from flask import current_app
from werkzeug import exceptions

import pjrpc.server


class JsonRPC:
    """
    `Flask <https://flask.palletsprojects.com/en/1.1.x/>`_ framework JSON-RPC extension class.

    :param path: JSON-RPC handler base path
    :param kwargs: arguments to be passed to the dispatcher :py:class:`pjrpc.server.Dispatcher`
    """

    def __init__(self, path: str, **kwargs: Any):
        self._path = path

        kwargs.setdefault('json_loader', flask.json.loads)
        kwargs.setdefault('json_dumper', flask.json.dumps)

        self._dispatcher = pjrpc.server.Dispatcher(**kwargs)

    @property
    def dispatcher(self) -> pjrpc.server.Dispatcher:
        """
        JSON-RPC method dispatcher.
        """

        return self._dispatcher

    def init_app(self, app: flask.Flask) -> None:
        """
        Initializes flask application with JSON-RPC extension.

        :param app: flask application instance
        """

        app.add_url_rule(self._path, methods=['POST'], view_func=self._rpc_handle)

    def _rpc_handle(self) -> flask.Response:
        """
        Handles JSON-RPC request.

        :returns: flask response
        """

        if not flask.request.is_json:
            raise exceptions.UnsupportedMediaType()

        try:
            flask.request.encoding_errors = 'strict'
            request_text = flask.request.get_data(as_text=True)
        except UnicodeDecodeError as e:
            raise exceptions.BadRequest() from e

        response_text = self._dispatcher.dispatch(request_text)
        if response_text is None:
            return current_app.response_class()
        else:
            return current_app.response_class(response_text, mimetype=current_app.config["JSONIFY_MIMETYPE"])
