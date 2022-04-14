#!/usr/bin/env python3
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
#
import asyncio
from pjrpc.client.backend import aio_pika as pjrpc_client
from pprint_log import pplog
from logging import basicConfig, INFO
from rich.logging import RichHandler
from rich.traceback import install


def setup_rich_logging() -> None:
    install(show_locals=False, extra_lines=0, suppress=[asyncio])
    keywords = ["List", "words", "to", "highlight", "in", "messages", "here:"]
    keywords += ["Methods:", "Result", "client", "sum", "hello", "3", "tick"]
    handler = RichHandler(show_time=False, show_level=False, keywords=keywords)
    basicConfig(level=INFO, format="%(message)s", handlers=[handler])


async def main() -> None:
    setup_rich_logging()
    client = pjrpc_client.Client(
        broker_url="amqp://guest:guest@localhost:5672/v1", queue_name="jsonrpc"
    )
    await client.connect()
    methods = []
    try:
        methods = await client.proxy.get_methods()
        pplog(("Methods:", methods))
        if "hello" in methods:
            hello = await client.proxy.hello()
            pplog(f"Result of hello = {hello}")
        if "sum" in methods:
            sum_result = await client.proxy.sum(a=1, b=2)
            pplog(f"Result of sum(1,2) = {sum_result}")
        if "tick" in methods:
            await client.notify("tick")
    except Exception as e:
        pplog(e)

    shutdown = "schedule_shutdown"
    shutdown = shutdown if shutdown in methods else "shutdown"
    await client.notify(shutdown)
    await asyncio.sleep(0.1)


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
