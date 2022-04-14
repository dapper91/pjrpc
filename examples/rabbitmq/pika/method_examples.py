#!/usr/bin/env python3
import asyncio
import logging
from typing import Any, Callable, Dict

RpcMethods = Dict[str, Callable[..., Any]]


def get_default_rpc_example_methods(logger: logging.Logger) -> RpcMethods:
    """Register the example methods and run the server until it is stopped"""
    calls = {"sum": 0}

    def sum(a: int, b: int) -> int:
        """RPC method for aio_pika_client.py's calls to sum(1, 2) -> 3"""
        calls["sum"] += 1
        return a + b

    def tick() -> None:
        """RPC method for examples/aio_pika_client.py's notification 'tick'"""
        logger.info(f'Notification tick: sum() called {calls["sum"]} times')

    def shutdown() -> None:
        """RPC method to terminate the server, for restart with updated code"""
        asyncio.get_event_loop().stop()

    def schedule_shutdown() -> None:
        """Schedule a shutdown, allows for an ack and response delivery"""
        loop = asyncio.get_event_loop()
        loop.call_later(0.05, loop.stop)

    return {
        "sum": sum,
        "tick": tick,
        "shutdown": shutdown,
        "schedule_shutdown": schedule_shutdown,
    }
