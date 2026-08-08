"""
FastApi JSON-RPC server integration.
"""
import functools as ft
import inspect
import json
from typing import Any, Callable, Iterable, Mapping, Optional, get_origin

import fastapi
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

import pjrpc
import pjrpc.server
from pjrpc.server import specs, utils
from pjrpc.server.dispatcher import AsyncExecutor, AsyncMiddlewareType, JSONEncoder, MethodRegistry


def is_fastapi_request(idx: int, name: str, annotation: Optional[type[Any]], default: Optional[Any]) -> bool:
    if annotation is None:
        return False

    annotation_origin = get_origin(annotation)
    return inspect.isclass(annotation_origin) and issubclass(annotation_origin, fastapi.Request)


FastApiDispatcher = pjrpc.server.AsyncDispatcher[fastapi.Request]


class Application:
    """
    `FastAPI <https://fastapi.tiangolo.com>`_ based JSON-RPC server.

    :param prefix: JSON-RPC handler base path
    :param http_app: FastApi application instance
    :param status_by_error: a function returns http status code by json-rpc error codes, 200 for all errors by default
    """

    def __init__(
        self,
        prefix: str = '',
        http_app: Optional[fastapi.FastAPI] = None,
        status_by_error: Callable[[tuple[int, ...]], int] = lambda codes: 200,
        executor: Optional[AsyncExecutor] = None,
        json_loader: Callable[..., Any] = json.loads,
        json_dumper: Callable[..., str] = json.dumps,
        json_encoder: type[JSONEncoder] = JSONEncoder,
        json_decoder: Optional[type[json.JSONDecoder]] = None,
        middlewares: Iterable[AsyncMiddlewareType[fastapi.Request]] = (),
        max_batch_size: Optional[int] = None,
    ):
        self._prefix = prefix.rstrip('/')
        self._http_app = http_app or fastapi.FastAPI()
        self._status_by_error = status_by_error

        self._executor: Optional[AsyncExecutor] = executor
        self._json_loader: Callable[..., Any] = json_loader
        self._json_dumper: Callable[..., str] = json_dumper
        self._json_encoder: type[JSONEncoder] = json_encoder
        self._json_decoder: Optional[type[json.JSONDecoder]] = json_decoder
        self._middlewares: Iterable[AsyncMiddlewareType[fastapi.Request]] = middlewares
        self._max_batch_size: Optional[int] = max_batch_size

        self._endpoints: dict[str, FastApiDispatcher] = {}
        self._subapps: dict[str, Application] = {}

    @property
    def prefix(self) -> str:
        return self._prefix

    @property
    def http_app(self) -> fastapi.FastAPI:
        """
        Fastapi application.
        """

        return self._http_app

    @property
    def endpoints(self) -> Mapping[str, FastApiDispatcher]:
        """
        JSON-RPC application registered endpoints.
        """

        return self._endpoints

    def add_methods(self, registry: MethodRegistry, endpoint: str = '') -> 'Application':
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

        self._http_app.mount(utils.join_path(self._prefix, prefix), subapp.http_app)
        self._subapps[prefix] = subapp

    def add_spec(self, spec: specs.Specification, endpoint: str = '', path: str = '') -> None:
        """
        Adds JSON-RPC specification of the provided endpoint to the provided path.

        :param spec: JSON-RPC specification
        :param endpoint: specification endpoint
        :param path: path under witch the specification will be accessible.
        """

        self._http_app.router.add_route(
            utils.join_path(self._prefix, endpoint, path),
            ft.partial(self._get_spec, endpoint=endpoint, spec=spec, path=path),
            methods=["GET"],
        )

    def add_spec_ui(self, path: str, ui: specs.BaseUI, spec_url: str) -> None:
        """
        Adds JSON-RPC specification ui.

        :param path: path under which ui will be accessible.
        :param ui: specification ui instance
        :param spec_url: specification url
        """

        ui_app = fastapi.FastAPI()
        ui_app.router.add_route(
            '/',
            ft.partial(self._ui_index_page, ui=ui, spec_url=spec_url), methods=["GET"],
        )
        ui_app.router.add_route(
            '/index.html',
            ft.partial(self._ui_index_page, ui=ui, spec_url=spec_url), methods=["GET"],
        )
        ui_app.router.mount('/', StaticFiles(directory=ui.get_static_folder()))

        self._http_app.mount(utils.join_path(self._prefix, path), ui_app)

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
                app_endpoints[utils.join_path(prefix, subapp._prefix, subprefix)] = dispatcher

        methods = {
            utils.remove_prefix(dispatcher_endpoint, endpoint): dispatcher.registry.values()
            for dispatcher_endpoint, dispatcher in app_endpoints.items()
            if dispatcher_endpoint.startswith(endpoint)
        }
        return spec.generate(
            root_endpoint=utils.join_path(base_path, endpoint),
            methods=methods,
        )

    async def _ui_index_page(self, request: fastapi.Request, ui: specs.BaseUI, spec_url: str) -> fastapi.Response:
        return fastapi.Response(content=ui.get_index_page(spec_url), media_type='text/html')

    def _get_endpoint(self, endpoint: str) -> FastApiDispatcher:
        endpoint = endpoint.rstrip('/')

        if endpoint not in self._endpoints:
            self._endpoints[endpoint] = dispatcher = FastApiDispatcher(
                executor=self._executor,
                json_loader=self._json_loader,
                json_dumper=self._json_dumper,
                json_encoder=self._json_encoder,
                json_decoder=self._json_decoder,
                middlewares=self._middlewares,
                max_batch_size=self._max_batch_size,
            )
            self._http_app.router.add_route(
                utils.join_path(self._prefix, endpoint),
                ft.partial(self._rpc_handle, dispatcher=dispatcher),
                methods=['POST'],
            )
        else:
            dispatcher = self._endpoints[endpoint]

        return dispatcher

    async def _get_spec(
        self,
        request: fastapi.Request,
        endpoint: str,
        spec: specs.Specification,
        path: str,
    ) -> fastapi.Response:
        base_path = utils.remove_suffix(request.scope['path'], suffix=utils.join_path(endpoint, path))
        schema = self.generate_spec(base_path=base_path, endpoint=endpoint.rstrip('/'), spec=spec)

        return JSONResponse(content=schema)

    async def _rpc_handle(self, http_request: fastapi.Request, dispatcher: FastApiDispatcher) -> fastapi.Response:
        """
        Handles JSON-RPC request.

        :param http_request: :py:class:`fastapi.Request`
        :returns: :py:class:`fastapi.Response`
        """

        content_type = http_request.headers.get("Content-Type", None)
        if content_type not in pjrpc.common.REQUEST_CONTENT_TYPES:
            raise fastapi.HTTPException(status_code=fastapi.status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

        try:
            request_body_bytes = await http_request.body()
            request_text = request_body_bytes.decode()
        except UnicodeDecodeError as e:
            raise fastapi.HTTPException(status_code=fastapi.status.HTTP_400_BAD_REQUEST) from e

        response = await dispatcher.dispatch(request_text, context=http_request)
        if response is None:
            return fastapi.Response()
        else:
            response_text, error_codes = response
            return JSONResponse(status_code=self._status_by_error(error_codes), content=response_text)
