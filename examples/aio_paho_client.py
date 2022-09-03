import asyncio
import logging
import ssl
from os import environ

from asyncio_paho import AsyncioPahoClient

import pjrpc
from pjrpc.client.backend import aio_paho


async def main() -> None:
    rpc = aio_paho.Client(debug=True)  # )
    rpc._client = AsyncioPahoClient(client_id=environ.get("MQTT_CLIENTID", ""))

    username = environ.get("MQTT_USERNAME", "")
    password = environ.get("MQTT_PASSWORD", "")
    rpc._client.username_pw_set(username, password)

    request_topic = environ.get("MQTT_RPC_REQUEST_TOPIC", "")
    response_topic = environ.get("MQTT_RPC_RESPONSE_TOPIC", "")
    rpc.topics(request_topic=request_topic, response_topic=response_topic)

    broker = environ.get("MQTT_BROKER")
    assert broker
    # Connect to broker using mqtts (mqtt+tls) on port 8883:
    rpc._client.tls_set(cert_reqs=ssl.CERT_NONE)
    rpc._client.tls_insecure_set(True)
    await rpc.connect(broker, port=8883)

    response = await rpc.send(pjrpc.Request('get_methods', params=None, id=1))
    assert response
    print(response.result)

    result = await rpc('get_methods')
    print(result)

    result = await rpc.proxy.get_methods()
    print(result)

    await rpc.notify('schedule_shutdown')


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    asyncio.run(main())
