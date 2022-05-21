import uuid

import flask

import pjrpc.server
from pjrpc.server.integration import flask as integration

methods_v1 = pjrpc.server.MethodRegistry()


@methods_v1.add
def add_user_v1(user: dict):
    user_id = uuid.uuid4().hex
    flask.current_app.users[user_id] = user

    return {'id': user_id, **user}


methods_v2 = pjrpc.server.MethodRegistry()


@methods_v2.add
def add_user_v2(user: dict):
    user_id = uuid.uuid4().hex
    flask.current_app.users[user_id] = user

    return {'id': user_id, **user}


app_v1 = flask.blueprints.Blueprint('v1', __name__)

json_rpc = integration.JsonRPC('/api/v1')
json_rpc.dispatcher.add_methods(methods_v1)
json_rpc.init_app(app_v1)


app_v2 = flask.blueprints.Blueprint('v2', __name__)

json_rpc = integration.JsonRPC('/api/v2')
json_rpc.dispatcher.add_methods(methods_v2)
json_rpc.init_app(app_v2)


app = flask.Flask(__name__)
app.register_blueprint(app_v1)
app.register_blueprint(app_v2)
app.users = {}


if __name__ == "__main__":
    app.run(port=8080)
