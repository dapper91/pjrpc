import functools as ft
import json
from typing import Any, List, Optional

import django.utils.functional
import django.utils.log
from django import urls
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest, HttpResponseNotAllowed
from django.utils.module_loading import import_string
from django.views.decorators.csrf import csrf_exempt

import pjrpc.server
from pjrpc.server import specs, utils


def require_http_methods(request_method_list):
    def decorator(func):
        @ft.wraps(func)
        def inner(self, request, *args, **kwargs):
            if request.method not in request_method_list:
                response = HttpResponseNotAllowed(request_method_list)
                django.utils.log.log_response(
                    'Method Not Allowed (%s): %s', request.method, request.path,
                    response=response,
                    request=request,
                )
                return response
            return func(self, request, *args, **kwargs)
        return inner
    return decorator


class JsonRPCSite:

    def __init__(self, path: str = '',  spec: Optional[specs.Specification] = None, **kwargs: Any):
        self._path = path
        self._spec = spec

        self._dispatcher = pjrpc.server.Dispatcher(**kwargs)
        self._urls = [
            urls.path(path, self._rpc_handle),
        ]

        if self._spec:
            self._urls.append(urls.path(utils.join_path(self._path, self._spec.path), self._generate_spec))

            if self._spec.ui and self._spec.ui_path:
                path = utils.join_path(self._path, self._spec.ui_path)
                self._urls.extend((
                    urls.path(utils.join_path(path, '/'), self._ui_index_page),
                    urls.path(utils.join_path(path, 'index.html'), self._ui_index_page),
                ))
                self._urls.extend(static(path, document_root=str(self._spec.ui.get_static_folder())))

    @property
    def dispatcher(self) -> pjrpc.server.Dispatcher:
        """
        JSON-RPC method dispatcher.
        """

        return self._dispatcher

    @property
    def urls(self) -> List[urls.path]:
        return self._urls

    @require_http_methods(['GET'])
    def _generate_spec(self, request: HttpRequest) -> HttpResponse:
        endpoint_path = utils.remove_suffix(request.path, suffix=self._spec.path)
        schema = self._spec.schema(path=endpoint_path, methods=self._dispatcher.registry.values())

        return HttpResponse(json.dumps(schema, indent=2, cls=specs.JSONEncoder), content_type='application/json')

    @require_http_methods(['GET'])
    def _ui_index_page(self, request: HttpRequest) -> HttpResponse:
        app_path = request.path.rsplit(self._spec.ui_path, maxsplit=1)[0]
        spec_full_path = utils.join_path(app_path, self._spec.path)

        return HttpResponse(self._spec.ui.get_index_page(spec_url=spec_full_path), content_type='text/html')

    @csrf_exempt
    @require_http_methods(['POST'])
    def _rpc_handle(self, request: HttpRequest) -> HttpResponse:
        """
        Handles JSON-RPC request.

        :param request: http request
        :returns: http response
        """

        if request.content_type != 'application/json':
            return HttpResponse(status=415)

        try:
            request_text = request.body.decode(request.encoding or 'utf8')
        except UnicodeDecodeError:
            return HttpResponseBadRequest()

        response_text = self._dispatcher.dispatch(request_text, context=request)
        if response_text is None:
            return HttpResponse()
        else:
            return HttpResponse(response_text, content_type='application/json')


class JsonRPCSites(django.utils.functional.LazyObject):
    def _setup(self):
        self._wrapped = []

        for path, endpoint in getattr(settings, 'JSONRPC_ENDPOINTS', {}).items():
            json_encoder = import_string(endpoint.get('JSON_ENCODER', 'pjrpc.server.dispatcher.JSONEncoder'))
            json_decoder = import_string(endpoint.get('JSON_DECODER', 'json.JSONDecoder'))
            spec = import_string(endpoint['SPEC']) if endpoint.get('SPEC', None) else None
            middlewares = [import_string(middleware) for middleware in endpoint.get('MIDDLEWARES', [])]
            error_handlers = {
                error: import_string(handler)
                for error, handler in endpoint.get('ERROR_HANDLERS', {}).items()
            }

            site = JsonRPCSite(
                path=path,
                spec=spec,
                json_encoder=json_encoder,
                json_decoder=json_decoder,
                middlewares=middlewares,
                error_handlers=error_handlers,
            )

            method_registry = import_string(endpoint['METHOD_REGISTRY'])
            site.dispatcher.add_methods(method_registry)

            self._wrapped.append(site)


jsonrpc_sites = JsonRPCSites()
