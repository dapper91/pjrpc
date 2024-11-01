"""
aiohttp JSON-RPC server integration.
"""

import functools as ft
import json
from typing import Any, Callable, Dict, Iterable, Mapping, Optional, Tuple

import aiohttp.web
from aiohttp import web

import pjrpc
from pjrpc.server import specs, utils


class Application:
    """
    `aiohttp <https://aiohttp.readthedocs.io/en/stable/web.html>`_ based JSON-RPC server.

    :param path: JSON-RPC handler base path
    :param spec: api specification instance
    :param app: aiohttp application instance
    :param status_by_error: a function returns http status code by json-rpc error codes, 200 for all errors by default
    :param kwargs: arguments to be passed to the dispatcher :py:class:`pjrpc.server.AsyncDispatcher`
    """

    def __init__(
        self,
        path: str = '',
        spec: Optional[specs.Specification] = None,
        specs: Iterable[specs.Specification] = (),
        app: Optional[web.Application] = None,
        status_by_error: Callable[[Tuple[int, ...]], int] = lambda codes: 200,
        **kwargs: Any,
    ):
        self._path = path = path.rstrip('/')
        self._specs = ([spec] if spec else []) + list(specs)
        self._app = app or web.Application()
        self._status_by_error = status_by_error
        self._dispatcher = pjrpc.server.AsyncDispatcher(**kwargs)
        self._endpoints: Dict[str, pjrpc.server.AsyncDispatcher] = {'': self._dispatcher}

        self._app.router.add_post(path, ft.partial(self._rpc_handle, dispatcher=self._dispatcher))

        for spec in self._specs:
            self._app.router.add_get(
                utils.join_path(path, spec.path),
                ft.partial(self._generate_spec, spec=spec),
            )

            if spec.ui and spec.ui_path:
                ui_app = web.Application()
                ui_app.router.add_get('/', ft.partial(self._ui_index_page, spec=spec))
                ui_app.router.add_get('/index.html', ft.partial(self._ui_index_page, spec=spec))
                ui_app.router.add_static('/', spec.ui.get_static_folder())

                self._app.add_subapp(utils.join_path(path, spec.ui_path), ui_app)

    @property
    def app(self) -> web.Application:
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

    def add_subapp(self, prefix: str, subapp: 'Application') -> None:
        """
        Adds sub-application.

        :param prefix: sub-application prefix
        :param subapp: sub-application to be added
        """

        prefix = prefix.rstrip('/')
        self._endpoints[prefix] = subapp.dispatcher
        self._app.add_subapp(utils.join_path(self._path, prefix), subapp.app)

    def add_endpoint(
        self,
        prefix: str,
        subapp: Optional[aiohttp.web.Application] = None,
        **kwargs: Any,
    ) -> pjrpc.server.AsyncDispatcher:
        """
        Adds additional endpoint.

        :param prefix: endpoint prefix
        :param subapp: aiohttp subapp the endpoint will be served on
        :param kwargs: arguments to be passed to the dispatcher :py:class:`pjrpc.server.Dispatcher`
        :return: dispatcher
        """

        prefix = prefix.rstrip('/')
        dispatcher = pjrpc.server.AsyncDispatcher(**kwargs)
        self._endpoints[prefix] = dispatcher

        if subapp:
            subapp.router.add_post('', ft.partial(self._rpc_handle, dispatcher=dispatcher))
            self._app.add_subapp(utils.join_path(self._path, prefix), subapp)
        else:
            self._app.router.add_post(
                utils.join_path(self._path, prefix),
                ft.partial(self._rpc_handle, dispatcher=dispatcher),
            )

        return dispatcher

    def generate_spec(self, spec: specs.Specification, path: str = '') -> Dict[str, Any]:
        methods = {path: dispatcher.registry.values() for path, dispatcher in self._endpoints.items()}
        return spec.schema(path=path, methods_map=methods)

    async def _generate_spec(self, request: web.Request, spec: specs.Specification) -> web.Response:
        endpoint_path = utils.remove_suffix(request.path, suffix=spec.path)
        schema = self.generate_spec(path=endpoint_path, spec=spec)

        return web.json_response(text=json.dumps(schema, cls=specs.JSONEncoder))

    async def _ui_index_page(self, request: web.Request, spec: specs.Specification) -> web.Response:
        assert spec.ui is not None, "spec is not set"

        app_path = request.path.rsplit(spec.ui_path, maxsplit=1)[0]
        spec_full_path = utils.join_path(app_path, spec.path)

        return web.Response(
            text=spec.ui.get_index_page(spec_url=spec_full_path),
            content_type='text/html',
        )

    async def _rpc_handle(self, http_request: web.Request, dispatcher: pjrpc.server.AsyncDispatcher) -> web.Response:
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
