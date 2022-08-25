import asyncio
import logging
from os import environ

import pjrpc
from pjrpc.client.backend import aio_paho


async def main() -> None:
    broker = environ.get("MQTT_BROKER")
    assert broker
    request_topic = environ.get("MQTT_RPC_REQUEST_TOPIC", "")
    response_topic = environ.get("MQTT_RPC_RESPONSE_TOPIC", "")
    clientid = environ.get("MQTT_CLIENTID", "")
    username = environ.get("MQTT_USERNAME", "")
    password = environ.get("MQTT_PASSWORD", "")

    client = aio_paho.Client(
        broker=broker,
        request_topic=request_topic,
        response_topic=response_topic,
        clientid=clientid,
        username=username,
        password=password,
    )
    await client.connect(debug=True)

    response = await client.send(pjrpc.Request('get_methods', params=None, id=1))
    assert response
    print(response.result)

    result = await client('get_methods')
    print(result)

    result = await client.proxy.get_methods()
    print(result)

    await client.notify('schedule_shutdown')


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    asyncio.run(main())
