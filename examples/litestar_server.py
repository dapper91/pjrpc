import uuid

from litestar import Request

import pjrpc.server
from pjrpc.server.integration import litestar

methods = pjrpc.server.MethodRegistry()


@methods.add(context='request')
async def add_user(request: Request, user: dict):
    user_id = uuid.uuid4().hex
    request.app.state['users'][user_id] = user

    return {'id': user_id, **user}


jsonrpc_app = litestar.Application('/api/v1', app=litestar.Litestar(debug=True))
jsonrpc_app.dispatcher.add_methods(methods)
jsonrpc_app.app.state['users'] = {}

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(jsonrpc_app.app, host='localhost', port=8080)
