import xjsonrpc
from xjsonrpc.client.backend import requests as xjsonrpc_client


client = xjsonrpc_client.Client('http://localhost/api/v1')

response: xjsonrpc.Response = client.send(xjsonrpc.Request('sum', params=[1, 2], id=1))
print(f"1 + 2 = {response.result}")

result = client('sum', a=1, b=2)
print(f"1 + 2 = {result}")

result = client.proxy.sum(1, 2)
print(f"1 + 2 = {result}")

client.notify('tick')
