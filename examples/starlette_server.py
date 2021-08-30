import uuid

import uvicorn

import pjrpc
from pjrpc.server.integration import starlette as integration

methods = pjrpc.server.MethodRegistry()
users = {}


@methods.add(context='request')
def add_user(request, user: dict):
    user_id = uuid.uuid4().hex
    users[user_id] = user

    return {'id': user_id, **user}


json_rpc = integration.Application('/api/v1')
json_rpc.dispatcher.add_methods(methods)


if __name__ == "__main__":
    uvicorn.run(json_rpc.app, port=8080)
