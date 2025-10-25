import pjrpc
from pjrpc.server.integration import flask as integration

methods = pjrpc.server.MethodRegistry()


@methods.add()
def sum(a: int, b: int) -> int:
    return a + b


json_rpc = integration.JsonRPC('/api/v1')
json_rpc.add_methods(methods)

if __name__ == "__main__":
    json_rpc.http_app.run(port=8080)
