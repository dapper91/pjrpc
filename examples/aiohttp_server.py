import uuid

from aiohttp import web

import pjrpc.server
from pjrpc.server.integration import aiohttp

methods = pjrpc.server.MethodRegistry()


@methods.add(context='request')
async def add_user(request: web.Request, user: dict):
    user_id = uuid.uuid4().hex
    request.app['users'][user_id] = user

    return {'id': user_id, **user}


app = aiohttp.Application('/api/v1')
app.dispatcher.add_methods(methods)
app['users'] = {}

if __name__ == "__main__":
    web.run_app(app, host='localhost', port=8080)
