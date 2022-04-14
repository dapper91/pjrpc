import asyncio

import xjsonrpc
from xjsonrpc.client.backend import aiohttp as xjsonrpc_client


async def main():
    async with xjsonrpc_client.Client('http://localhost/api/v1') as client:
        response = await client.send(xjsonrpc.Request('sum', params=[1, 2], id=1))
        print(f"1 + 2 = {response.result}")

        result = await client('sum', a=1, b=2)
        print(f"1 + 2 = {result}")

        result = await client.proxy.sum(1, 2)
        print(f"1 + 2 = {result}")

        await client.notify('tick')


asyncio.run(main())
