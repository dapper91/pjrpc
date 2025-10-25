import asyncio

import pjrpc
from pjrpc.client.backend import aiohttp as pjrpc_client


async def main():
    async with pjrpc_client.Client('http://localhost:8080/api/v1') as client:
        async with client.batch() as batch:
            batch.send(pjrpc.Request('sum', [2, 2], id=1))
            batch.send(pjrpc.Request('sub', [2, 2], id=2))
            batch.send(pjrpc.Request('div', [2, 2], id=3))
            batch.send(pjrpc.Request('mult', [2, 2], id=4))

        response = batch.get_response()
        print(f"2 + 2 = {response[0].result}")
        print(f"2 - 2 = {response[1].result}")
        print(f"2 / 2 = {response[2].result}")
        print(f"2 * 2 = {response[3].result}")

        async with client.batch() as batch:
            batch('sum', 2, 2)
            batch('sub', 2, 2)
            batch('div', 2, 2)
            batch('mult', 2, 2)

        result = batch.get_results()
        print(f"2 + 2 = {result[0]}")
        print(f"2 - 2 = {result[1]}")
        print(f"2 / 2 = {result[2]}")
        print(f"2 * 2 = {result[3]}")

        async with client.batch() as batch:
            batch.proxy.sum(2, 2)
            batch.proxy.sub(2, 2)
            batch.proxy.div(2, 2)
            batch.proxy.mult(2, 2)

        result = batch.get_results()
        print(f"2 + 2 = {result[0]}")
        print(f"2 - 2 = {result[1]}")
        print(f"2 / 2 = {result[2]}")
        print(f"2 * 2 = {result[3]}")

        async with client.batch() as batch:
            batch.notify('tick')
            batch.notify('tack')


asyncio.run(main())
