"""
aiohttp JSON-RPC server integration.
"""

from aiohttp import web

import pjrpc


class Application(web.Application):
    """
    `aiohttp <https://aiohttp.readthedocs.io/en/stable/web.html>`_ based JSON-RPC server.

    :param path: JSON-RPC handler base path
    :param app_args: arguments to be passed to :py:class:`aiohttp.web.Application`
    :param kwargs: arguments to be passed to the dispatcher :py:class:`pjrpc.server.AsyncDispatcher`
    """

    def __init__(self, path='', app_args=None, **kwargs):
        super().__init__(**(app_args or {}))
        self._dispatcher = pjrpc.server.AsyncDispatcher(**kwargs)

        self.router.add_post(path, self.rpc_handle)

    @property
    def dispatcher(self):
        """
        JSON-RPC method dispatcher.
        """

        return self._dispatcher

    async def rpc_handle(self, http_request):
        """
        Handles JSON-RPC request.

        :param http_request: :py:class:`aiohttp.web.Response`
        :returns: :py:class:`aiohttp.web.Request`
        """

        if http_request.content_type != 'application/json':
            raise web.HTTPUnsupportedMediaType()

        try:
            request_text = await http_request.text()
        except UnicodeDecodeError as e:
            raise web.HTTPBadRequest() from e

        response_text = await self._dispatcher.dispatch(request_text, context=http_request)
        if response_text is None:
            return web.Response()
        else:
            return web.json_response(text=response_text)
