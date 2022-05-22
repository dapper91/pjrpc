"""
aiohttp JSON-RPC server integration.
"""

import functools as ft
import json
from typing import Any, Dict, Mapping, Optional, cast

from starlette import exceptions, routing
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import Response
from starlette.staticfiles import StaticFiles

import pjrpc
from pjrpc.common.typedefs import Func
from pjrpc.server import specs, utils


def async_partial(func: Func, *bound_args: Any, **bound_kwargs: Any) -> Func:
    @ft.wraps(func)
    async def wrapped(*args: Any, **kwargs: Any) -> Any:
        return await func(*bound_args, *args, **bound_kwargs, **kwargs)

    return cast(Func, wrapped)


class Application:
    """
    `aiohttp <https://aiohttp.readthedocs.io/en/stable/web.html>`_ based JSON-RPC server.

    :param path: JSON-RPC handler base path
    :param app_args: arguments to be passed to :py:class:`aiohttp.web.Application`
    :param kwargs: arguments to be passed to the dispatcher :py:class:`pjrpc.server.AsyncDispatcher`
    """

    def __init__(
        self,
        path: str = '',
        spec: Optional[specs.Specification] = None,
        app: Optional[Starlette] = None,
        **kwargs: Any
    ):
        self._path = path.rstrip('/')
        self._spec = spec
        self._app = app or Starlette()
        self._dispatcher = pjrpc.server.AsyncDispatcher(**kwargs)
        self._endpoints: Dict[str, pjrpc.server.AsyncDispatcher] = {'': self._dispatcher}

        self._app.add_route(self._path, async_partial(self._rpc_handle, dispatcher=self._dispatcher), methods=['POST'])

        if self._spec:
            self._app.add_route(utils.join_path(self._path, self._spec.path), self._generate_spec, methods=['GET'])

            if self._spec.ui and self._spec.ui_path:
                ui_path = utils.join_path(self._path, self._spec.ui_path)

                self._app.add_route(utils.join_path(ui_path, '/'), self._ui_index_page)
                self._app.add_route(utils.join_path(ui_path, 'index.html'), self._ui_index_page)
                self._app.routes.append(
                    routing.Mount(ui_path, app=StaticFiles(directory=str(self._spec.ui.get_static_folder()))),
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
            async_partial(self._rpc_handle, dispatcher=self._dispatcher),
            methods=['POST'],
        )

        return dispatcher

    async def _generate_spec(self, request: Request) -> Response:
        assert self._spec is not None, "spec is not set"

        endpoint_path = utils.remove_suffix(request.url.path, suffix=self._spec.path)

        methods = {path: dispatcher.registry.values() for path, dispatcher in self._endpoints.items()}
        schema = self._spec.schema(path=endpoint_path, methods_map=methods)

        return Response(
            content=json.dumps(schema, cls=specs.JSONEncoder),
            media_type='application/json',
        )

    async def _ui_index_page(self, request: Request) -> Response:
        assert self._spec is not None and self._spec.ui is not None, "spec is not set"

        app_path = request.url.path.rsplit(self._spec.ui_path, maxsplit=1)[0]
        spec_full_path = utils.join_path(app_path, self._spec.path)

        return Response(
            content=self._spec.ui.get_index_page(spec_url=spec_full_path),
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

        response_text = await dispatcher.dispatch(request_text, context=http_request)
        if response_text is None:
            return Response()
        else:
            return Response(content=response_text, media_type=pjrpc.common.DEFAULT_CONTENT_TYPE)
