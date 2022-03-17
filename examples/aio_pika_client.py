import asyncio

import pjrpc
from pjrpc.client.backend import aio_pika as pjrpc_client


async def main():
    client = pjrpc_client.Client('amqp://guest:guest@localhost:5672/v1', 'jsonrpc')
    await client.connect()

    response: pjrpc.Response = await client.send(pjrpc.Request('sum', params=[1, 2], id=1))
    print(f"1 + 2 = {response.result}")

    result = await client('sum', a=1, b=2)
    print(f"1 + 2 = {result}")

    result = await client.proxy.sum(1, 2)
    print(f"1 + 2 = {result}")

    await client.notify('tick')

    await client.notify('schedule_shutdown')

if __name__ == "__main__":
    asyncio.run(main())
