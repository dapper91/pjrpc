import asyncio
import logging
import ssl
from os import environ
from typing import Tuple

from asyncio_paho import AsyncioPahoClient

import pjrpc
from pjrpc.client.backend import aio_paho


def get_broker() -> Tuple[str, str, int]:
    broker = environ.get("MQTT_BROKER")
    assert broker
    try:
        scheme_idx = broker.index("://")
        transport = broker[:scheme_idx]
        broker = broker[scheme_idx + 3:]
        print(transport)
        if transport == "wss":
            transport = "websockets"
    except ValueError:
        transport = "tcp"
    try:
        port = int(broker[broker.index(":") + 1:])
        broker = broker[: broker.index(":")]
    except ValueError:
        port = 1883
    print(transport, broker, port)
    return transport, broker, port


async def main() -> None:
    rpc = aio_paho.Client(debug=True)
    transport, broker, port = get_broker()
    rpc.client = AsyncioPahoClient(
        transport=transport,
        client_id=environ.get("MQTT_CLIENTID", ""),
    )
    if port == 443:
        rpc.client.tls_set("pki.autonoma.cloud-rootca.cer")
    elif port == 8883:
        rpc.client.tls_set(cert_reqs=ssl.CERT_NONE)
        # To disable verification of the server hostname in the server certificate:
        # rpc._client.tls_insecure_set(True)

    username = environ.get("MQTT_USERNAME", "")
    password = environ.get("MQTT_PASSWORD", "")
    rpc.client.username_pw_set(username, password)

    request_topic = environ.get("MQTT_RPC_REQUEST_TOPIC", "")
    response_topic = environ.get("MQTT_RPC_RESPONSE_TOPIC", "")
    rpc.topics(request_topic=request_topic, response_topic=response_topic)

    await rpc.connect(broker, port)

    await rpc.notify('schedule_restart')
    await asyncio.sleep(1)
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
