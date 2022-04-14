import uuid

from aiohttp import web

import xjsonrpc.server
from xjsonrpc.server.integration import aiohttp

methods = xjsonrpc.server.MethodRegistry()


@methods.view(context='request', prefix='user')
class UserView(xjsonrpc.server.ViewMixin):

    def __init__(self, request: web.Request):
        super().__init__()

        self._users = request.app['users']

    async def add(self, user: dict):
        user_id = uuid.uuid4().hex
        self._users[user_id] = user

        return {'id': user_id, **user}

    async def get(self, user_id: str):
        user = self._users.get(user_id)
        if not user:
            xjsonrpc.exc.JsonRpcError(code=1, message='not found')

        return user


jsonrpc_app = aiohttp.Application('/api/v1')
jsonrpc_app.dispatcher.add_methods(methods)
jsonrpc_app.app['users'] = {}

if __name__ == "__main__":
    web.run_app(jsonrpc_app.app, host='localhost', port=8080)
