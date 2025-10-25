import uuid

import flask

import pjrpc.server
from pjrpc.server.integration import flask as integration

methods_v1 = pjrpc.server.MethodRegistry()


@methods_v1.add(name="add_user")
def add_user_v1(user: dict):
    user_id = uuid.uuid4().hex
    flask.current_app.users[user_id] = user

    return {'id': user_id, **user}


methods_v2 = pjrpc.server.MethodRegistry()


@methods_v2.add(name="add_user")
def add_user_v2(user: dict):
    user_id = uuid.uuid4().hex
    flask.current_app.users[user_id] = user

    return {'id': user_id, **user}


json_rpc = integration.JsonRPC('/api')
json_rpc.http_app.users = {}

json_rpc_v1 = integration.JsonRPC(http_app=flask.Blueprint("v1", __name__))
json_rpc_v1.add_methods(methods_v1)
json_rpc.add_subapp('/v1', json_rpc_v1)

json_rpc_v2 = integration.JsonRPC(http_app=flask.Blueprint("v2", __name__))
json_rpc_v2.add_methods(methods_v2)
json_rpc.add_subapp('/v2', json_rpc_v2)


if __name__ == "__main__":
    json_rpc.http_app.run(port=8080)
