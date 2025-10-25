import logging

from aiohttp import web

import pjrpc.server
from pjrpc.server.integration import aiohttp

methods = pjrpc.server.MethodRegistry()


@methods.add(pass_context='request')
async def sum(request: web.Request, a: int, b: int) -> int:
    return a + b


@methods.add(pass_context='request')
async def sub(request: web.Request, a: int, b: int) -> int:
    return a - b


@methods.add(pass_context='request')
async def div(request: web.Request, a: int, b: int) -> float:
    return a / b


@methods.add(pass_context='request')
async def mult(request: web.Request, a: int, b: int) -> int:
    return a * b


@methods.add()
async def ping() -> None:
    logging.info("ping")


jsonrpc_app = aiohttp.Application('/api/v1')
jsonrpc_app.add_methods(methods)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    web.run_app(jsonrpc_app.http_app, host='localhost', port=8080)
