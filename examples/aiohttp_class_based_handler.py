import uuid

from aiohttp import web

import pjrpc.server
from pjrpc.server.integration import aiohttp

methods = pjrpc.server.MethodRegistry()


@methods.view(context='request', prefix='user')
class UserView(pjrpc.server.View):

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
            pjrpc.exc.JsonRpcError(code=1, message='not found')

        return user


app = aiohttp.Application('/api/v1')
app.dispatcher.add_methods(methods)
app['users'] = {}

if __name__ == "__main__":
    web.run_app(app, host='localhost', port=8080)
