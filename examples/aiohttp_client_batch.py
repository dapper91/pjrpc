import asyncio

import pjrpc
from pjrpc.client.backend import aiohttp as pjrpc_client


async def main():
    async with pjrpc_client.Client('http://localhost:8080/api/v1') as client:

        batch_response = await client.batch.send(
            pjrpc.BatchRequest(
                pjrpc.Request('sum', [2, 2], id=1),
                pjrpc.Request('sub', [2, 2], id=2),
                pjrpc.Request('div', [2, 2], id=3),
                pjrpc.Request('mult', [2, 2], id=4),
            ),
        )
        print(f"2 + 2 = {batch_response[0].result}")
        print(f"2 - 2 = {batch_response[1].result}")
        print(f"2 / 2 = {batch_response[2].result}")
        print(f"2 * 2 = {batch_response[3].result}")

        result = await client.batch('sum', 2, 2)('sub', 2, 2)('div', 2, 2)('mult', 2, 2).call()
        print(f"2 + 2 = {result[0]}")
        print(f"2 - 2 = {result[1]}")
        print(f"2 / 2 = {result[2]}")
        print(f"2 * 2 = {result[3]}")

        result = await client.batch[
            ('sum', 2, 2),
            ('sub', 2, 2),
            ('div', 2, 2),
            ('mult', 2, 2),
        ]
        print(f"2 + 2 = {result[0]}")
        print(f"2 - 2 = {result[1]}")
        print(f"2 / 2 = {result[2]}")
        print(f"2 * 2 = {result[3]}")

        result = await client.batch.proxy.sum(2, 2).sub(2, 2).div(2, 2).mult(2, 2).call()
        print(f"2 + 2 = {result[0]}")
        print(f"2 - 2 = {result[1]}")
        print(f"2 / 2 = {result[2]}")
        print(f"2 * 2 = {result[3]}")

        await client.batch.notify('tick').notify('tack').call()


asyncio.run(main())
