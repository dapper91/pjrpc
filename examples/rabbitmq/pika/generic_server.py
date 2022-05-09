#!/usr/bin/env python
# Start a rabbitmq container: cd examples/pika; docker-compose up
#
# Then, add the vhost v1 and give the user guest permssion to use it:
# docker_exec="docker exec -it rmq_rabbit_1"
# $docker_exec rabbitmqctl add_vhost v1
# $docker_exec rabbitmqctl set_permissions -p v1 guest ".*" ".*" ".*"
#
# - Then start the server and the client
# - To delete the jsonrpc queue to force the server to recreate it, use:
# docker exec -it rmq_rabbit_1 rabbitmqadmin delete queue name jsonrpc
import logging
from typing import Any, cast, List
from pjrpc.server import MethodRegistry


class GenericServer:
    """Generic base class for creating specific example RPC servers"""

    logger: logging.Logger
    registry: MethodRegistry

    def __new__(cls, **kwargs: Any) -> "GenericServer":
        """Provide logger at instance.logger by logging.basicConfig(kwargs)"""
        logging.basicConfig(**kwargs)
        instance = super(GenericServer, cls).__new__(cls)
        instance.logger = logging.getLogger()
        instance.registry = MethodRegistry()

        @instance.registry.add
        def get_methods() -> List[str]:
            """Return the list of RPC methods provided by the server"""
            return [x for x in instance.registry.keys() if x != "get_methods"]

        return instance

    def __init__(self, **kwargs: Any) -> None:
        """Initializes the server with logging and example RPC methods"""
        import asyncio
        import pformat_logger
        from functools import partial
        from pprint import pformat

        self.width = pformat_logger.get_terminal_width()
        self.pformat = partial(pformat, sort_dicts=False, width=self.width)

        @self.registry.add
        def schedule_shutdown() -> None:
            """Schedule a shutdown, allows for an ack and response delivery"""
            loop = asyncio.get_event_loop()
            loop.call_later(0.05, loop.stop)


class ExtendedGenericServer(GenericServer):
    """of GenericServer which can be identified by a hello string"""

    def __new__(cls, greeting: str, **kwargs: Any) -> "ExtendedGenericServer":
        return cast(
            ExtendedGenericServer,
            super(ExtendedGenericServer, cls).__new__(cls, **kwargs),
        )

    def __init__(self, origin: str = None, **kwargs: Any) -> None:
        from pformat_logger import pplog

        # server.pplog provides a logger which pretty-prints using pformat()
        self.pplog = pplog
        if origin:
            self.name = f"JSON-RPC Server[aio_pika] (via {origin})"
            self.pplog(f"{self.name} is starting up")
        super().__init__()

        @self.registry.add
        async def hello(**kwargs: Any) -> List[str]:
            return [origin]


def extended_jsonrpc_server_with_rich(greeting: str) -> None:
    """Setup and run an extended JSON-RPC[AIO-PIKA] server with rich logging"""
    import asyncio
    import contextlib
    import server_middleware
    from method_examples import register_example_methods
    from rich.logging import RichHandler
    from pjrpc.server.integration.aio_pika import Executor

    keywords = ["JSON-RPC", "Server", "hello", "from", "generic_server.py"]
    handler = RichHandler(show_time=False, show_level=False, keywords=keywords)
    server = ExtendedGenericServer(
        greeting,  # Optional message to be shown on startup and sent to client
        level=logging.INFO,
        format="%(message)s",
        handlers=[handler],
    )
    executor = Executor(
        broker_url="amqp://guest:guest@localhost:5672/v1",
        queue_name="jsonrpc",
        middlewares=(
            server_middleware.serialize_requests(),
            server_middleware.log_requests(server.logger),
            server_middleware.stop_on_exception(server.logger),
        ),
    )
    register_example_methods(server.registry, server.logger)
    executor.dispatcher.add_methods(server.registry)

    async def demo_task_printing_a_message() -> None:
        await asyncio.sleep(1)
        print("This is the demo task!")

    loop = asyncio.get_event_loop()
    loop.create_task(demo_task_printing_a_message())
    loop.run_until_complete(executor.start(queue_args={"durable": False}))
    loop.run_forever()
    with contextlib.suppress(RuntimeError):
        loop.run_until_complete(executor.shutdown())


def run_extended_rpcserver_with_origin() -> None:
    """Run ExtendedGenericServer(with rich logging and an additional task)"""
    import __main__
    from pathlib import Path

    extended_jsonrpc_server_with_rich(Path(__main__.__file__).name)


if __name__ == "__main__":
    run_extended_rpcserver_with_origin()
