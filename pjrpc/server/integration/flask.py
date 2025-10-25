"""
Flask JSON-RPC extension.
"""

import functools as ft
import json
from typing import Any, Callable, Iterable, Optional, Union

import flask
from flask import current_app
from werkzeug import exceptions

import pjrpc.server
from pjrpc.server import specs, utils
from pjrpc.server.dispatcher import Executor, JSONEncoder, MethodRegistry, MiddlewareType

FlaskDispatcher = pjrpc.server.Dispatcher[None]


class JsonRPC:
    """
    `Flask <https://flask.palletsprojects.com/en/1.1.x/>`_ framework JSON-RPC extension class.

    :param prefix: JSON-RPC handler base path
    :param status_by_error: a function returns http status code by json-rpc error codes, 200 for all errors by default
    """

    def __init__(
        self,
        prefix: str = '',
        http_app: Optional[Union[flask.Flask, flask.Blueprint]] = None,
        status_by_error: Callable[[tuple[int, ...]], int] = lambda codes: 200,
        executor: Optional[Executor] = None,
        json_loader: Callable[..., Any] = json.loads,
        json_dumper: Callable[..., str] = json.dumps,
        json_encoder: type[JSONEncoder] = JSONEncoder,
        json_decoder: Optional[type[json.JSONDecoder]] = None,
        middlewares: Iterable[MiddlewareType[None]] = (),
        max_batch_size: Optional[int] = None,
    ):
        self._prefix = prefix.rstrip('/')
        self._http_app = http_app or flask.Flask(__name__)
        self._status_by_error = status_by_error

        self._executor = executor
        self._json_loader = json_loader
        self._json_dumper = json_dumper
        self._json_encoder = json_encoder
        self._json_decoder = json_decoder
        self._middlewares = middlewares
        self._max_batch_size = max_batch_size

        self._endpoints: dict[str, FlaskDispatcher] = {}
        self._subapps: dict[str, JsonRPC] = {}

    @property
    def http_app(self) -> Union[flask.Flask, flask.Blueprint]:
        """
        aiohttp application.
        """

        return self._http_app

    @property
    def endpoints(self) -> dict[str, FlaskDispatcher]:
        """
        JSON-RPC application registered endpoints.
        """

        return self._endpoints

    def add_methods(self, registry: MethodRegistry, endpoint: str = '') -> 'JsonRPC':
        """
        Adds methods to the provided endpoint.

        :param registry: methods registry
        :param endpoint: endpoint path
        """

        dispatcher = self._get_endpoint(endpoint)
        dispatcher.add_methods(registry)
        return self

    def add_subapp(self, prefix: str, subapp: 'JsonRPC') -> None:
        """
        Adds sub-application accessible under provided prefix.

        :param prefix: path under which sub-application is accessed.
        :param subapp: sub-application instance
        """

        assert isinstance(subapp.http_app, flask.Blueprint), "subapp must be a sub-application instance"

        prefix = prefix.rstrip('/')
        if not prefix:
            raise ValueError("prefix cannot be empty")

        for dispatcher in subapp.endpoints.values():
            dispatcher.add_middlewares(*self._middlewares, before=True)

        self._http_app.register_blueprint(subapp.http_app, url_prefix=utils.join_path(self._prefix, prefix))
        self._subapps[prefix] = subapp

    def add_spec(self, spec: specs.Specification, endpoint: str = '', path: str = '') -> None:
        """
        Adds JSON-RPC specification of the provided endpoint to the provided path.

        :param spec: JSON-RPC specification
        :param endpoint: specification endpoint
        :param path: path under witch the specification will be accessible.
        """

        self._http_app.add_url_rule(
            f"/{utils.join_path(self._prefix, endpoint, path)}",
            methods=['GET'],
            endpoint=self._get_spec.__name__,
            view_func=ft.partial(self._get_spec, endpoint=endpoint, spec=spec, path=path),
        )

    def add_spec_ui(self, path: str, ui: specs.BaseUI, spec_url: str) -> None:
        """
        Adds JSON-RPC specification ui.

        :param path: path under which ui will be accessible.
        :param ui: specification ui instance
        :param spec_url: specification url
        """

        ui_app = flask.Blueprint(ui.__class__.__name__, __name__)
        ui_app.add_url_rule(
            '/',
            methods=['GET'],
            endpoint=self._ui_index_page.__name__,
            view_func=ft.partial(self._ui_index_page, ui=ui, spec_url=spec_url),
        )
        ui_app.add_url_rule(
            '/index.html',
            methods=['GET'],
            endpoint=f'{self._ui_index_page.__name__}-index',
            view_func=ft.partial(self._ui_index_page, ui=ui, spec_url=spec_url),
        )
        ui_app.add_url_rule(
            '/<path:filename>',
            methods=['GET'],
            endpoint=self._ui_static.__name__,
            view_func=ft.partial(self._ui_static, ui=ui),
        )

        self._http_app.register_blueprint(ui_app, url_prefix=utils.join_path(self._prefix, path))

    def generate_spec(self, spec: specs.Specification, base_path: str = '', endpoint: str = '') -> dict[str, Any]:
        """
        Generates JSON-RPC specification of the provided endpoint.

        :param spec: JSON-RPC specification
        :param base_path: specification base path
        :param endpoint: endpoint the specification is generated for
        """

        app_endpoints = self._endpoints
        for prefix, subapp in self._subapps.items():
            for subprefix, dispatcher in subapp.endpoints.items():
                app_endpoints[utils.join_path(prefix, subprefix)] = dispatcher

        methods = {
            utils.remove_prefix(dispatcher_endpoint, endpoint): dispatcher.registry.values()
            for dispatcher_endpoint, dispatcher in app_endpoints.items()
            if dispatcher_endpoint.startswith(endpoint)
        }
        return spec.generate(
            root_endpoint=utils.join_path(base_path, endpoint),
            methods=methods,
        )

    def _ui_index_page(self, ui: specs.BaseUI, spec_url: str) -> flask.Response:
        return current_app.response_class(response=ui.get_index_page(spec_url), content_type='text/html')

    def _ui_static(self, ui: specs.BaseUI, filename: str) -> flask.Response:
        return flask.send_from_directory(ui.get_static_folder(), filename)

    def _get_endpoint(self, endpoint: str) -> FlaskDispatcher:
        endpoint = endpoint.rstrip('/')

        if endpoint not in self._endpoints:
            self._endpoints[endpoint] = dispatcher = FlaskDispatcher(
                executor=self._executor,
                json_loader=self._json_loader,
                json_dumper=self._json_dumper,
                json_encoder=self._json_encoder,
                json_decoder=self._json_decoder,
                middlewares=self._middlewares,
                max_batch_size=self._max_batch_size,
            )
            self._http_app.add_url_rule(
                f"/{utils.join_path(self._prefix, endpoint)}",
                methods=['POST'],
                endpoint="rpc_handle",
                view_func=ft.partial(self._rpc_handle, dispatcher=dispatcher),
            )
        else:
            dispatcher = self._endpoints[endpoint]

        return dispatcher

    def _get_spec(self, endpoint: str, spec: specs.Specification, path: str) -> flask.Response:
        base_path = utils.remove_suffix(flask.request.path, suffix=utils.join_path(endpoint, path))
        schema = self.generate_spec(base_path=base_path, endpoint=endpoint.rstrip('/'), spec=spec)

        return current_app.response_class(
            self._json_dumper(schema, cls=self._json_encoder),
            mimetype=pjrpc.common.DEFAULT_CONTENT_TYPE,
        )

    def _rpc_handle(self, dispatcher: FlaskDispatcher) -> flask.Response:
        """
        Handles JSON-RPC request.

        :returns: flask response
        """

        if not flask.request.is_json:
            raise exceptions.UnsupportedMediaType()

        try:
            request_text = flask.request.get_data(as_text=True)
        except UnicodeDecodeError as e:
            raise exceptions.BadRequest() from e

        response = dispatcher.dispatch(request_text, context=None)
        if response is None:
            return current_app.response_class()
        else:
            response_text, error_codes = response
            return current_app.response_class(
                response_text,
                status=self._status_by_error(error_codes),
                mimetype=pjrpc.common.DEFAULT_CONTENT_TYPE,
            )
