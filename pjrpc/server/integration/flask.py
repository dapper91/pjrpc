"""
Flask JSON-RPC extension.
"""

import functools as ft
import json
from typing import Any, Callable, Dict, Iterable, Optional, Tuple, Union

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

    def __init__(
        self,
        path: str,
        spec: Optional[specs.Specification] = None,
        specs: Iterable[specs.Specification] = (),
        status_by_error: Callable[[Tuple[int, ...]], int] = lambda codes: 200,
        **kwargs: Any,
    ):
        self._path = path.rstrip('/')
        self._specs = ([spec] if spec else []) + list(specs)
        self._status_by_error = status_by_error

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
        if blueprint is not None:
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

        for spec in self._specs:
            app.add_url_rule(
                utils.join_path(self._path, spec.path),
                methods=['GET'],
                endpoint=self._generate_spec.__name__,
                view_func=ft.partial(self._generate_spec, spec=spec),
            )

            if spec.ui and spec.ui_path:
                path = utils.join_path(self._path, spec.ui_path)
                app.add_url_rule(
                    f'{path}/',
                    methods=['GET'],
                    endpoint=self._ui_index_page.__name__,
                    view_func=ft.partial(self._ui_index_page, spec=spec),
                )
                app.add_url_rule(
                    f'{path}/index.html',
                    methods=['GET'],
                    endpoint=f'{self._ui_index_page.__name__}-index',
                    view_func=ft.partial(self._ui_index_page, spec=spec),
                )
                app.add_url_rule(
                    f'{path}/<path:filename>',
                    methods=['GET'],
                    endpoint=self._ui_static.__name__,
                    view_func=ft.partial(self._ui_static, spec=spec),
                )

    def generate_spec(self, spec: specs.Specification, path: str = '') -> Dict[str, Any]:
        methods = {path: dispatcher.registry.values() for path, dispatcher in self._endpoints.items()}
        return spec.schema(path=path, methods_map=methods)

    def _generate_spec(self, spec: specs.Specification) -> flask.Response:
        endpoint_path = utils.remove_suffix(flask.request.path, suffix=spec.path)
        schema = self.generate_spec(spec, path=endpoint_path)

        return current_app.response_class(
            json.dumps(schema, cls=specs.JSONEncoder),
            mimetype=pjrpc.common.DEFAULT_CONTENT_TYPE,
        )

    def _ui_index_page(self, spec: specs.Specification) -> flask.Response:
        assert spec.ui is not None, "spec is not set"

        app_path = flask.request.path.rsplit(spec.ui_path, maxsplit=1)[0]
        spec_full_path = utils.join_path(app_path, spec.path)

        return current_app.response_class(
            response=spec.ui.get_index_page(spec_url=spec_full_path),
            content_type='text/html',
        )

    def _ui_static(self, filename: str, spec: specs.Specification) -> flask.Response:
        assert spec.ui is not None, "spec is not set"

        return flask.send_from_directory(spec.ui.get_static_folder(), filename)

    def _rpc_handle(self, dispatcher: pjrpc.server.Dispatcher) -> flask.Response:
        """
        Handles JSON-RPC request.

        :returns: flask response
        """

        if not flask.request.is_json:
            raise exceptions.UnsupportedMediaType()

        try:
            flask.request.encoding_errors = 'strict'  # type: ignore[attr-defined]
            request_text = flask.request.get_data(as_text=True)
        except UnicodeDecodeError as e:
            raise exceptions.BadRequest() from e

        response = dispatcher.dispatch(request_text)
        if response is None:
            return current_app.response_class()
        else:
            response_text, error_codes = response
            return current_app.response_class(
                response_text,
                status=self._status_by_error(error_codes),
                mimetype=pjrpc.common.DEFAULT_CONTENT_TYPE,
            )
