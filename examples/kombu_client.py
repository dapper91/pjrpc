import xjsonrpc
from xjsonrpc.client.backend import kombu as xjsonrpc_client


client = xjsonrpc_client.Client(
    'amqp://guest:guest@localhost:5672/v1',
    'jsonrpc',
    # Compatible with queue of examples/aio_pika_*
    # and works better with examples/kombu_server.py:
    result_queue_args={"durable": False},
)


response: xjsonrpc.Response = client.send(xjsonrpc.Request('sum', params=[1, 2], id=1))
print(f"1 + 2 = {response.result}")

result = client('sum', a=1, b=2)
print(f"1 + 2 = {result}")

result = client.proxy.sum(1, 2)
print(f"1 + 2 = {result}")

client.notify('tick')
