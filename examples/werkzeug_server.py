import uuid

import werkzeug

import pjrpc.server
from pjrpc.server.integration import werkzeug as integration

methods = pjrpc.server.MethodRegistry()


@methods.add(context='request')
def add_user(request: werkzeug.Request, user: dict):
    user_id = uuid.uuid4().hex
    request.environ['app'].users[user_id] = user

    return {'id': user_id, **user}


app = integration.JsonRPC('/api/v1')
app.dispatcher.add_methods(methods)
app.users = {}


if __name__ == '__main__':
    werkzeug.serving.run_simple('127.0.0.1', 8080, app)
