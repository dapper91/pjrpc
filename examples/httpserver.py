import uuid
import http.server
import socketserver

import pjrpc.server
from pjrpc.server.integration import httpserver as integration

methods = pjrpc.server.MethodRegistry()


@methods.add(context='request')
def add_user(request: http.server.BaseHTTPRequestHandler, user: dict):
    user_id = uuid.uuid4().hex
    request.server.users[user_id] = user

    return {'id': user_id, **user}


class ThreadingJsonRpcServer(socketserver.ThreadingMixIn, integration.JsonRpcServer):
    users = {}


with ThreadingJsonRpcServer(("localhost", 8080)) as server:
    server.dispatcher.add_methods(methods)

    server.serve_forever()
