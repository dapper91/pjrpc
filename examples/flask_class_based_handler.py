import uuid

import flask

import pjrpc
from pjrpc.server.integration import flask as integration

app = flask.Flask(__name__)

methods = pjrpc.server.MethodRegistry()


@methods.view(prefix='user')
class UserView(pjrpc.server.ViewMixin):

    def __init__(self):
        super().__init__()

        self._users = flask.current_app.users

    def add(self, user: dict):
        user_id = uuid.uuid4().hex
        self._users[user_id] = user

        return {'id': user_id, **user}

    def get(self, user_id: str):
        user = self._users.get(user_id)
        if not user:
            pjrpc.exc.JsonRpcError(code=1, message='not found')

        return user


json_rpc = integration.JsonRPC('/api/v1')
json_rpc.dispatcher.add_methods(methods)

app.users = {}

json_rpc.init_app(app)

if __name__ == "__main__":
    app.run(port=8080)
