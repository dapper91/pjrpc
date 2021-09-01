"""
Flask JSON-RPC extension.
"""

import json
import functools as ft
from typing import Any, Dict, Optional, Union

import flask
from flask import current_app
from werkzeug import exceptions

import pjrpc.server
from pjrpc.server import specs, utils


class JsonRPC:
    """
    `Flask <https://flask.palletsprojects.com/en/1.1.x/>`_ framework JSON-RPC extension class.

    :param path: JSON-RPC handler base path
    :param spec: JSON-RPC specification
    :param kwargs: arguments to be passed to the dispatcher :py:class:`pjrpc.server.Dispatcher`
    """

    def __init__(self, path: str, spec: Optional[specs.Specification] = None, **kwargs: Any):
        self._path = path.rstrip('/')
        self._spec = spec

        kwargs.setdefault('json_loader', flask.json.loads)
        kwargs.setdefault('json_dumper', flask.json.dumps)

        self._dispatcher = pjrpc.server.Dispatcher(**kwargs)
        self._endpoints: Dict[str, pjrpc.server.Dispatcher] = {'': self._dispatcher}
        self._blueprints: Dict[str, flask.Blueprint] = {}

    @property
    def dispatcher(self) -> pjrpc.server.Dispatcher:
        """
        JSON-RPC method dispatcher.
        """

        return self._dispatcher

    @property
    def endpoints(self) -> Dict[str, pjrpc.server.Dispatcher]:
        """
        JSON-RPC application registered endpoints.
        """

        return self._endpoints

    def add_endpoint(
        self,
        prefix: str,
        blueprint: Optional[flask.Blueprint] = None,
        **kwargs: Any,
    ) -> pjrpc.server.Dispatcher:
        """
        Adds additional endpoint.

        :param prefix: endpoint prefix
        :param blueprint: flask blueprint the endpoint will be served on
        :param kwargs: arguments to be passed to the dispatcher :py:class:`pjrpc.server.Dispatcher`
        :return: dispatcher
        """

        prefix = prefix.rstrip('/')
        dispatcher = pjrpc.server.Dispatcher(**kwargs)

        self._endpoints[prefix] = dispatcher
        self._blueprints[prefix] = blueprint

        return dispatcher

    def init_app(self, app: Union[flask.Flask, flask.Blueprint]) -> None:
        """
        Initializes flask application with JSON-RPC extension.

        :param app: flask application instance
        """

        for prefix, dispatcher in self._endpoints.items():
            path = utils.join_path(self._path, prefix)
            blueprint = self._blueprints.get(prefix)

            (blueprint or app).add_url_rule(
                path,
                methods=['POST'],
                view_func=ft.partial(self._rpc_handle, dispatcher=dispatcher),
                endpoint=path.replace('/', '_'),
            )
            if blueprint:
                app.register_blueprint(blueprint)

        if self._spec:
            app.add_url_rule(
                utils.join_path(self._path, self._spec.path),
                methods=['GET'],
                view_func=self._generate_spec,
            )

            if self._spec.ui and self._spec.ui_path:
                path = utils.join_path(self._path, self._spec.ui_path)
                app.add_url_rule(f'{path}/', methods=['GET'], view_func=self._ui_index_page)
                app.add_url_rule(f'{path}/index.html', methods=['GET'], view_func=self._ui_index_page)
                app.add_url_rule(f'{path}/<path:filename>', methods=['GET'], view_func=self._ui_static)

    def _generate_spec(self) -> flask.Response:
        endpoint_path = utils.remove_suffix(flask.request.path, suffix=self._spec.path)
        methods = {path: dispatcher.registry.values() for path, dispatcher in self._endpoints.items()}
        schema = self._spec.schema(path=endpoint_path, methods_map=methods)

        return current_app.response_class(
            json.dumps(schema, indent=2, cls=specs.JSONEncoder),
            mimetype=current_app.config["JSONIFY_MIMETYPE"],
        )

    def _ui_index_page(self) -> flask.Response:
        app_path = flask.request.path.rsplit(self._spec.ui_path, maxsplit=1)[0]
        spec_full_path = utils.join_path(app_path, self._spec.path)

        return current_app.response_class(
            response=self._spec.ui.get_index_page(spec_url=spec_full_path),
            content_type='text/html',
        )

    def _ui_static(self, filename: str) -> flask.Response:
        return flask.send_from_directory(self._spec.ui.get_static_folder(), filename)

    def _rpc_handle(self, dispatcher: pjrpc.server.Dispatcher) -> flask.Response:
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

        response_text = dispatcher.dispatch(request_text)
        if response_text is None:
            return current_app.response_class()
        else:
            return current_app.response_class(response_text, mimetype=current_app.config["JSONIFY_MIMETYPE"])
