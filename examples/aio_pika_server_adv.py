#!/usr/bin/env python3
""" Advanced aio_pika server example:
- uses functions which can be used as blueprints for larger examples
- has an ExampleExecutor subclass to provide default settings for the Executor
- sets up logging unless logging is already configured
- support for strict typechecking using mypy --strict
"""

import asyncio
import contextlib
import logging
from middleware_examples import log_requests
from pjrpc.server import MethodRegistry
from pjrpc.server.integration.aio_pika import Executor
from typing import Any, Callable, List

RpcMethods = List[Callable[..., Any]]


def run_executor(
    broker_url: str, queue_name: str, methods: RpcMethods, **kwargs: Any
) -> None:
    """Register the passed methods and run the server until it is stopped"""

    executor = Executor(broker_url, queue_name, **kwargs)
    registry = MethodRegistry()
    for method in methods:
        registry.add_methods(method)
    executor.dispatcher.add_methods(registry)

    # Everything is set up, now run the executor:
    loop = asyncio.get_event_loop()
    loop.run_until_complete(executor.start())
    loop.run_forever()
    with contextlib.suppress(RuntimeError):
        loop.run_until_complete(executor.shutdown())


def start_advanced_example_aio_pika_server() -> None:
    """Register the example methods and run the server until it is stopped"""
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger()
    calls = {"sum": 0}

    def sum(a: int, b: int) -> int:
        """RPC method for aio_pika_client.py's calls to sum(1, 2) -> 3"""
        calls["sum"] += 1
        return a + b

    def tick() -> None:
        """RPC method for examples/aio_pika_client.py's notification 'tick'"""
        logger.info(f'run notification tick: sum called {calls["sum"]} times')

    def shutdown() -> None:
        """RPC method to terminate the server, for restart with updated code"""
        asyncio.get_running_loop().stop()

    run_executor(
        "amqp://guest:guest@localhost:5672/v1",
        "jsonrpc",
        [sum, tick, shutdown],
        middlewares=(log_requests(logger),),
    )


if __name__ == "__main__":
    start_advanced_example_aio_pika_server()
