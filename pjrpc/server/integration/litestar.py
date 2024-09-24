"""
litestar JSON-RPC server integration.
"""

import functools as ft
import json
from typing import Any, Dict, Mapping, Optional

from litestar import handlers, Litestar, Response, Request, Router, exceptions, static_files

import pjrpc
from pjrpc.server import specs, utils


class Application:
    """
    `litestar <https://litestar.dev>`_ based JSON-RPC server.

    :param path: JSON-RPC handler base path
    :param app_args: arguments to be passed to :py:class:`litestar.app.Application`
    :param kwargs: arguments to be passed to the dispatcher :py:class:`pjrpc.server.AsyncDispatcher`
    """

    def __init__(
        self,
        path: str = '',
        spec: Optional[specs.Specification] = None,
        app: Optional[Litestar] = None,
        **kwargs: Any,
    ):
        self._path = path.rstrip('/')
        self._spec = spec
        self._app = app or Litestar()
        self._router = Router('/', route_handlers=())
        self._dispatcher = pjrpc.server.AsyncDispatcher(**kwargs)
        self._endpoints: Dict[str, pjrpc.server.AsyncDispatcher] = {'': self._dispatcher}

        self._router.register(
            handlers.route(path=self._path, http_method='POST')(self._rpc_handle),
        )

        if self._spec:
            # self._router.register(
            #     handlers.route(
            #         path=utils.join_path(self._path, self._spec.path),
            #         http_method='GET',
            #     )(self._generate_spec)
            # )

            if self._spec.ui and self._spec.ui_path:
                ui_path = utils.join_path(self._path, self._spec.ui_path)

                # self._router.register(
                #     handlers.route(
                #         path=utils.join_path(ui_path, '/'),
                #         http_method='GET',
                #     )(self._ui_index_page),
                # )
                # self._router.register(
                #     handlers.route(
                #         path=utils.join_path(ui_path, 'index.html'),
                #         http_method='GET',
                #     )(self._ui_index_page),
                # )
                # self._router.register(
                #     static_files.create_static_files_router(
                #         path=ui_path,
                #         directories=[str(self._spec.ui.get_static_folder())]
                #     )
                # )

        self._app.register(self._router)

    @property
    def app(self) -> Litestar:
        """
        litestar application.
        """

        return self._app

    @property
    def router(self) -> Router:
        """
        litestar application router.
        """

        return self._router

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

        self._app.register(
            handlers.route(path=utils.join_path(self._path, prefix), http_method='POST')(self._rpc_handle),
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

    async def _rpc_handle(self, request: Request) -> Response:
        """
        Handles JSON-RPC request.

        :param request: :py:class:`litestar.response.Response`
        :returns: :py:class:`litestar.connection.request.Request`
        """

        if request.headers.get('Content-Type') not in pjrpc.common.REQUEST_CONTENT_TYPES:
            raise exceptions.HTTPException(status_code=415)

        try:
            request_data = await request.body()
            request_text = request_data.decode()
        except UnicodeDecodeError as e:
            raise exceptions.HTTPException(status_code=400) from e

        response_text = await self._dispatcher.dispatch(request_text, context=request)
        if response_text is None:
            return Response(content='')
        else:
            return Response(content=response_text, media_type=pjrpc.common.DEFAULT_CONTENT_TYPE)
