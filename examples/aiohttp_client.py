import asyncio

import pjrpc
from pjrpc.client.backend import aiohttp as pjrpc_client


async def main():
    async with pjrpc_client.Client('http://localhost:8080/api/v1') as client:
        response = await client.send(pjrpc.Request('sum', params=[1, 2], id=1))
        print(f"1 + 2 = {response.result}")

        result = await client('sum', a=1, b=2)
        print(f"1 + 2 = {result}")

        result = await client.proxy.sum(1, 2)
        print(f"1 + 2 = {result}")

        await client.notify('ping')


asyncio.run(main())
