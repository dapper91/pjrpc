"""
aiohttp JSON-RPC server integration.
"""

import functools as ft
import inspect
import json
from typing import Any, Callable, Iterable, Mapping, Optional, Self

from aiohttp import web

import pjrpc
from pjrpc.server import specs, utils
from pjrpc.server.dispatcher import AsyncExecutor, AsyncMiddlewareType, JSONEncoder, MethodRegistry


def is_aiohttp_request(idx: int, name: str, annotation: Optional[type[Any]], default: Optional[Any]) -> bool:
    if annotation is None:
        return False

    return inspect.isclass(annotation) and issubclass(annotation, web.Request)


AioHttpDispatcher = pjrpc.server.AsyncDispatcher[web.Request]


class Application:
    """
    `aiohttp <https://aiohttp.readthedocs.io/en/stable/web.html>`_ based JSON-RPC server.

    :param prefix: JSON-RPC handler base path
    :param http_app: aiohttp application instance
    :param status_by_error: a function returns http status code by json-rpc error codes, 200 for all errors by default
    """

    def __init__(
        self,
        prefix: str = '',
        http_app: Optional[web.Application] = None,
        status_by_error: Callable[[tuple[int, ...]], int] = lambda codes: 200,
        executor: Optional[AsyncExecutor] = None,
        json_loader: Callable[..., Any] = json.loads,
        json_dumper: Callable[..., str] = json.dumps,
        json_encoder: type[JSONEncoder] = JSONEncoder,
        json_decoder: Optional[type[json.JSONDecoder]] = None,
        middlewares: Iterable[AsyncMiddlewareType[web.Request]] = (),
        max_batch_size: Optional[int] = None,
    ):
        self._prefix = prefix.rstrip('/')
        self._http_app = http_app or web.Application()
        self._status_by_error = status_by_error

        self._executor: Optional[AsyncExecutor] = executor
        self._json_loader: Callable[..., Any] = json_loader
        self._json_dumper: Callable[..., str] = json_dumper
        self._json_encoder: type[JSONEncoder] = json_encoder
        self._json_decoder: Optional[type[json.JSONDecoder]] = json_decoder
        self._middlewares: Iterable[AsyncMiddlewareType[web.Request]] = middlewares
        self._max_batch_size: Optional[int] = max_batch_size

        self._endpoints: dict[str, AioHttpDispatcher] = {}
        self._subapps: dict[str, Application] = {}

    @property
    def http_app(self) -> web.Application:
        """
        aiohttp application.
        """

        return self._http_app

    @property
    def endpoints(self) -> Mapping[str, AioHttpDispatcher]:
        """
        JSON-RPC application registered endpoints.
        """

        return self._endpoints

    def add_methods(self, registry: MethodRegistry, endpoint: str = '') -> Self:
        """
        Adds methods to the provided endpoint.

        :param registry: methods registry
        :param endpoint: endpoint path
        """

        dispatcher = self._get_endpoint(endpoint)
        dispatcher.add_methods(registry)
        return self

    def add_subapp(self, prefix: str, subapp: 'Application') -> None:
        """
        Adds sub-application accessible under provided prefix.

        :param prefix: path under which sub-application is accessed.
        :param subapp: sub-application instance
        """

        prefix = prefix.rstrip('/')
        if not prefix:
            raise ValueError("prefix cannot be empty")

        for dispatcher in subapp.endpoints.values():
            dispatcher.add_middlewares(*self._middlewares, before=True)

        self._http_app.add_subapp(utils.join_path(self._prefix, prefix), subapp.http_app)
        self._subapps[prefix] = subapp

    def add_spec(self, spec: specs.Specification, endpoint: str = '', path: str = '') -> None:
        """
        Adds JSON-RPC specification of the provided endpoint to the provided path.

        :param spec: JSON-RPC specification
        :param endpoint: specification endpoint
        :param path: path under witch the specification will be accessible.
        """

        self._http_app.router.add_get(
            utils.join_path(self._prefix, endpoint, path),
            ft.partial(self._get_spec, endpoint=endpoint, spec=spec, path=path),
        )

    def add_spec_ui(self, path: str, ui: specs.BaseUI, spec_url: str) -> None:
        """
        Adds JSON-RPC specification ui.

        :param path: path under which ui will be accessible.
        :param ui: specification ui instance
        :param spec_url: specification url
        """

        ui_app = web.Application()
        ui_app.router.add_get('/', ft.partial(self._ui_index_page, ui=ui, spec_url=spec_url))
        ui_app.router.add_get('/index.html', ft.partial(self._ui_index_page, ui=ui, spec_url=spec_url))
        ui_app.router.add_static('/', ui.get_static_folder())

        self._http_app.add_subapp(utils.join_path(self._prefix, path), ui_app)

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

    async def _ui_index_page(self, request: web.Request, ui: specs.BaseUI, spec_url: str) -> web.Response:
        return web.Response(text=ui.get_index_page(spec_url), content_type='text/html')

    def _get_endpoint(self, endpoint: str) -> AioHttpDispatcher:
        endpoint = endpoint.rstrip('/')

        if endpoint not in self._endpoints:
            self._endpoints[endpoint] = dispatcher = AioHttpDispatcher(
                executor=self._executor,
                json_loader=self._json_loader,
                json_dumper=self._json_dumper,
                json_encoder=self._json_encoder,
                json_decoder=self._json_decoder,
                middlewares=self._middlewares,
                max_batch_size=self._max_batch_size,
            )
            self._http_app.router.add_post(
                utils.join_path(self._prefix, endpoint),
                ft.partial(self._rpc_handle, dispatcher=dispatcher),
            )
        else:
            dispatcher = self._endpoints[endpoint]

        return dispatcher

    async def _get_spec(
        self,
        request: web.Request,
        endpoint: str,
        spec: specs.Specification,
        path: str,
    ) -> web.Response:
        base_path = utils.remove_suffix(request.path, suffix=utils.join_path(endpoint, path))
        schema = self.generate_spec(base_path=base_path, endpoint=endpoint.rstrip('/'), spec=spec)

        return web.json_response(text=self._json_dumper(schema, cls=self._json_encoder))

    async def _rpc_handle(self, http_request: web.Request, dispatcher: AioHttpDispatcher) -> web.Response:
        """
        Handles JSON-RPC request.

        :param http_request: :py:class:`aiohttp.web.Response`
        :returns: :py:class:`aiohttp.web.Request`
        """

        if http_request.content_type not in pjrpc.common.REQUEST_CONTENT_TYPES:
            raise web.HTTPUnsupportedMediaType()

        try:
            request_text = await http_request.text()
        except UnicodeDecodeError as e:
            raise web.HTTPBadRequest() from e

        response = await dispatcher.dispatch(request_text, context=http_request)
        if response is None:
            return web.Response()
        else:
            response_text, error_codes = response
            return web.json_response(status=self._status_by_error(error_codes), text=response_text)
