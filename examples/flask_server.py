import uuid

import flask

import pjrpc
from pjrpc.server import MethodRegistry
from pjrpc.server.integration import flask as integration

app = flask.Flask(__name__)

methods = pjrpc.server.MethodRegistry()


@methods.add
def add_user(user: dict):
    user_id = uuid.uuid4().hex
    flask.current_app.users[user_id] = user

    return {'id': user_id, **user}


json_rpc = integration.JsonRPC('/api/v1')
json_rpc.dispatcher.add_methods(methods)

app.users = {}

json_rpc.init_app(app)

if __name__ == "__main__":
    app.run(port=8080)
