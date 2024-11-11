"""
aiohttp JSON-RPC server integration.
"""

import functools as ft
import json
from typing import Any, Callable, Dict, Iterable, Mapping, Optional, Tuple

from starlette import exceptions, routing
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import Response
from starlette.staticfiles import StaticFiles

import pjrpc
from pjrpc.server import specs, utils


class Application:
    """
    `starlette <https://www.starlette.io/>`_ based JSON-RPC server.

    :param path: JSON-RPC handler base path
    :param spec: api specification instance
    :param app: starlette application instance
    :param status_by_error: a function returns http status code by json-rpc error codes, 200 for all errors by default
    :param kwargs: arguments to be passed to the dispatcher :py:class:`pjrpc.server.AsyncDispatcher`
    """

    def __init__(
        self,
        path: str = '',
        spec: Optional[specs.Specification] = None,
        specs: Iterable[specs.Specification] = (),
        app: Optional[Starlette] = None,
        status_by_error: Callable[[Tuple[int, ...]], int] = lambda codes: 200,
        **kwargs: Any,
    ):
        self._path = path = path.rstrip('/')
        self._specs = ([spec] if spec else []) + list(specs)
        self._app = app or Starlette()
        self._status_by_error = status_by_error
        self._dispatcher = pjrpc.server.AsyncDispatcher(**kwargs)
        self._endpoints: Dict[str, pjrpc.server.AsyncDispatcher] = {'': self._dispatcher}

        self._app.add_route(path, ft.partial(self._rpc_handle, dispatcher=self._dispatcher), methods=['POST'])

        for spec in self._specs:
            self._app.add_route(
                utils.join_path(path, spec.path),
                ft.partial(self._generate_spec, spec=spec),
                methods=['GET'],
            )

            if spec.ui and spec.ui_path:
                ui_path = utils.join_path(path, spec.ui_path)

                self._app.add_route(
                    utils.join_path(ui_path, '/'), ft.partial(self._ui_index_page, spec=spec),
                )
                self._app.add_route(
                    utils.join_path(ui_path, 'index.html'), ft.partial(self._ui_index_page, spec=spec),
                )
                self._app.routes.append(
                    routing.Mount(ui_path, app=StaticFiles(directory=str(spec.ui.get_static_folder()))),
                )

    @property
    def app(self) -> Starlette:
        """
        aiohttp application.
        """

        return self._app

    @property
    def dispatcher(self) -> pjrpc.server.AsyncDispatcher:
        """
        JSON-RPC method dispatcher.
        """

        return self._dispatcher

    @property
    def endpoints(self) -> Mapping[str, pjrpc.server.AsyncDispatcher]:
        """
        JSON-RPC application registered endpoints.
        """

        return self._endpoints

    def add_endpoint(self, prefix: str, **kwargs: Any) -> pjrpc.server.AsyncDispatcher:
        """
        Adds additional endpoint.

        :param prefix: endpoint prefix
        :param kwargs: arguments to be passed to the dispatcher :py:class:`pjrpc.server.Dispatcher`
        :return: dispatcher
        """

        dispatcher = pjrpc.server.AsyncDispatcher(**kwargs)
        self._endpoints[prefix] = dispatcher

        self._app.add_route(
            utils.join_path(self._path, prefix),
            ft.partial(self._rpc_handle, dispatcher=dispatcher),
            methods=['POST'],
        )

        return dispatcher

    def generate_spec(self, spec: specs.Specification, path: str = '') -> Dict[str, Any]:
        methods = {path: dispatcher.registry.values() for path, dispatcher in self._endpoints.items()}
        return spec.schema(path=path, methods_map=methods)

    async def _generate_spec(self, request: Request, spec: specs.Specification) -> Response:
        endpoint_path = utils.remove_suffix(request.url.path, suffix=spec.path)
        schema = self.generate_spec(path=endpoint_path, spec=spec)

        return Response(
            content=json.dumps(schema, cls=specs.JSONEncoder),
            media_type='application/json',
        )

    async def _ui_index_page(self, request: Request, spec: specs.Specification) -> Response:
        assert spec.ui is not None, "spec is not set"

        app_path = request.url.path.rsplit(spec.ui_path, maxsplit=1)[0]
        spec_full_path = utils.join_path(app_path, spec.path)

        return Response(
            content=spec.ui.get_index_page(spec_url=spec_full_path),
            media_type='text/html',
        )

    async def _rpc_handle(self, http_request: Request, dispatcher: pjrpc.server.AsyncDispatcher) -> Response:
        """
        Handles JSON-RPC request.

        :param http_request: :py:class:`aiohttp.web.Response`
        :returns: :py:class:`aiohttp.web.Request`
        """

        if http_request.headers['Content-Type'] not in pjrpc.common.REQUEST_CONTENT_TYPES:
            raise exceptions.HTTPException(415)

        try:
            request_data = await http_request.body()
            request_text = request_data.decode()
        except UnicodeDecodeError as e:
            raise exceptions.HTTPException(400) from e

        response = await dispatcher.dispatch(request_text, context=http_request)
        if response is None:
            return Response()
        else:
            response_text, error_codes = response
            return Response(
                status_code=self._status_by_error(error_codes),
                content=response_text,
                media_type=pjrpc.common.DEFAULT_CONTENT_TYPE,
            )
