import logging
import uuid

from aiohttp import web

import pjrpc.server
from pjrpc.server.integration import aiohttp

methods_v1 = pjrpc.server.MethodRegistry()


@methods_v1.add(name="add_user", pass_context='request')
async def add_user_v1(request: web.Request, user: dict) -> dict:
    user_id = uuid.uuid4().hex
    request.config_dict['users'][user_id] = user

    return {'id': user_id, **user}


methods_v2 = pjrpc.server.MethodRegistry()


@methods_v2.add(name="add_user", pass_context='request')
async def add_user_v2(request: web.Request, user: dict) -> dict:
    user_id = uuid.uuid4().hex
    request.config_dict['users'][user_id] = user

    return {'id': user_id, **user}


app = web.Application()
app['users'] = {}

app_v1 = aiohttp.Application()
app_v1.add_methods(methods_v1)
app.add_subapp('/api/v1', app_v1.http_app)


app_v2 = aiohttp.Application()
app_v2.add_methods(methods_v2)
app.add_subapp('/api/v2', app_v2.http_app)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    web.run_app(app, host='localhost', port=8080)
