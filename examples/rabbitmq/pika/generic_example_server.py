#!/usr/bin/env python
import asyncio
import contextlib
import logging
import method_examples  # example implementations of PJRPC server methods
import server_middleware
from pjrpc.server import MethodRegistry
from pjrpc.server.integration.aio_pika import Executor
from typing import Any, List


class GenericExampleServer:
    """Generic base class for creating specific example RPC servers"""

    broker_url: str
    queue_name: str
    logger: logging.Logger
    registry: MethodRegistry
    middlewares: List[server_middleware.Middleware]

    def __new__(cls, **kwargs: Any) -> "GenericExampleServer":
        # sourcery skip: instance-method-first-arg-name
        logging.basicConfig(level=logging.INFO, format="%(message)s")
        instance = super(GenericExampleServer, cls).__new__(cls)
        instance.logger = logging.getLogger()
        logsetup = kwargs.get("logsetup")
        if logsetup:
            logsetup(instance)
        instance.registry = MethodRegistry()
        return instance

    def __init__(self, **kwargs: Any) -> None:
        """Initializes the server with logging"""
        methods = method_examples.get_default_rpc_example_methods(self.logger)
        for method in methods.values():
            self.registry.add_methods(method)

        @self.registry.add
        def get_methods() -> List[str]:
            """Return the list of RPC methods provided by the server"""
            return [x for x in self.registry.keys() if x != "get_methods"]

    def run_executor(
        self, broker_url: str, queue_name: str, *args: Any, **kwargs: Any
    ) -> None:
        """Run the excutor of the server until it is stopped"""
        executor = Executor(broker_url, queue_name, *args, **kwargs)
        executor.dispatcher.add_methods(self.registry)

        # Everything is set up, now run the executor:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(executor.start())
        loop.run_forever()
        with contextlib.suppress(RuntimeError):
            loop.run_until_complete(executor.shutdown())


if __name__ == "__main__":
    """As an example user of this class, run the server from server_hello.py"""
    from server_hello import run_aio_pika_example_server

    run_aio_pika_example_server("Hello from generic_example_server.py!")
