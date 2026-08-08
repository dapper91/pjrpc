import logging

import fastapi

import pjrpc.server
from pjrpc.server.integration import fastapi as integration

methods = pjrpc.server.MethodRegistry()


@methods.add()
async def sum(a: int, b: int) -> int:
    return a + b


@methods.add()
async def sub(a: int, b: int) -> int:
    return a - b


@methods.add()
async def div(a: int, b: int) -> float:
    return a / b


@methods.add()
async def mult(a: int, b: int) -> int:
    return a * b


@methods.add()
async def ping() -> None:
    logging.info("ping")


jsonrpc_app = integration.Application('/api/v1')
jsonrpc_app.add_methods(methods)

app = fastapi.FastAPI()
app.mount("/rpc", jsonrpc_app.http_app)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
