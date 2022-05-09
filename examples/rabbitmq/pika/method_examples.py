#!/usr/bin/env python3
from logging import Logger
from typing import Any, Callable, Dict
from pjrpc.server import MethodRegistry as Registry

RpcMethods = Dict[str, Callable[..., Any]]


def register_example_methods(methods: Registry, logger: Logger) -> RpcMethods:
    """Register the example methods and run the server until it is stopped"""
    calls = {"sum": 0}

    @methods.add
    def sum(a: int, b: int) -> int:
        """RPC method for aio_pika_client.py's calls to sum(1, 2) -> 3"""
        calls["sum"] += 1
        return a + b

    @methods.add
    def tick() -> None:
        """RPC method for examples/aio_pika_client.py's notification 'tick'"""
        logger.info(f'Notification tick: sum() called {calls["sum"]} times')


if __name__ == '__main__':
    from generic_server import run_extended_rpcserver_with_origin

    run_extended_rpcserver_with_origin()
