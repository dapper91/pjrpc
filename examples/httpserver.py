import http.server
import socketserver
import uuid

import pjrpc
import pjrpc.server


class JsonRpcHandler(http.server.BaseHTTPRequestHandler):
    """
    JSON-RPC handler.
    """

    def do_POST(self):
        """
        Handles JSON-RPC request.
        """

        content_type = self.headers.get('Content-Type')
        if content_type not in pjrpc.common.REQUEST_CONTENT_TYPES:
            self.send_error(http.HTTPStatus.UNSUPPORTED_MEDIA_TYPE)
            return

        try:
            content_length = int(self.headers.get('Content-Length', -1))
            request_text = self.rfile.read(content_length).decode()
        except UnicodeDecodeError:
            self.send_error(http.HTTPStatus.BAD_REQUEST)
            return

        response = self.server.dispatcher.dispatch(request_text, context=self)
        if response is None:
            self.send_response_only(http.HTTPStatus.OK)
            self.end_headers()
        else:
            response_text, error_codes = response
            self.send_response(http.HTTPStatus.OK)
            self.send_header("Content-type", pjrpc.common.DEFAULT_CONTENT_TYPE)
            self.end_headers()

            self.wfile.write(response_text.encode())


class JsonRpcServer(http.server.HTTPServer):
    """
    :py:class:`http.server.HTTPServer` based JSON-RPC server.

    :param path: JSON-RPC handler base path
    :param kwargs: arguments to be passed to the dispatcher :py:class:`pjrpc.server.Dispatcher`
    """

    def __init__(self, server_address, RequestHandlerClass=JsonRpcHandler, bind_and_activate=True, **kwargs):
        super().__init__(server_address, RequestHandlerClass, bind_and_activate)
        self._dispatcher = pjrpc.server.Dispatcher(**kwargs)

    @property
    def dispatcher(self):
        """
        JSON-RPC method dispatcher.
        """

        return self._dispatcher


methods = pjrpc.server.MethodRegistry()


@methods.add(context='request')
def add_user(request: http.server.BaseHTTPRequestHandler, user: dict):
    user_id = uuid.uuid4().hex
    request.server.users[user_id] = user

    return {'id': user_id, **user}


class ThreadingJsonRpcServer(socketserver.ThreadingMixIn, JsonRpcServer):
    users = {}


with ThreadingJsonRpcServer(("localhost", 8080)) as server:
    server.dispatcher.add_methods(methods)

    server.serve_forever()
