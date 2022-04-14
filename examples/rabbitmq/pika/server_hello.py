#!/usr/bin/env python
import pprint_log
import server_middleware
from typing import Any, cast, List
import generic_example_server


class HelloServer(generic_example_server.GenericExampleServer):
    """Example using GenericExampleServer which adds a hello RPC method"""

    def __new__(cls, greeting: str, **kwargs: Any) -> "HelloServer":
        # sourcery skip: instance-method-first-arg-name
        return cast(
            HelloServer, super(HelloServer, cls).__new__(cls, **kwargs)
        )

    def __init__(self, greeting: str, **kwargs: Any) -> None:
        pprint_log.pplog(f"Greeting from HelloServer is: {greeting}")

        @self.registry.add
        async def hello(**kwargs: Any) -> List[str]:
            return [greeting]

        # Here, you can open files or connections for your methods above.
        # Then call the __init__() method of the superclass:
        super().__init__()


def run_aio_pika_example_server(greeting: str) -> None:
    """Setup and run the HelloServer with rich logging and middlewares"""
    from logging_setup import init_rich_logger

    server = HelloServer(greeting, logsetup=init_rich_logger)
    server.run_executor(
        broker_url="amqp://guest:guest@localhost:5672/v1",
        queue_name="jsonrpc",
        middlewares=(
            server_middleware.serialize_requests(),
            server_middleware.log_requests(server.logger),
            server_middleware.stop_on_exception(server.logger),
        ),
    )


if __name__ == "__main__":
    run_aio_pika_example_server("Hello from this HelloServer!")
