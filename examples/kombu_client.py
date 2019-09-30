import pjrpc
from pjrpc.client.backend import kombu as pjrpc_client


client = pjrpc_client.Client('amqp://guest:guest@localhost:5672/v1', 'jsonrpc')


response: pjrpc.Response = client.send(pjrpc.Request('sum', params=[1, 2]))
print(f"1 + 2 = {response.result}")

result = client('sum', a=1, b=2)
print(f"1 + 2 = {result}")

result = client.proxy.sum(1, 2)
print(f"1 + 2 = {result}")

client.notify('tick')
