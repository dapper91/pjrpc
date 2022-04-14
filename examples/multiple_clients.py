import xjsonrpc
from xjsonrpc.client.backend import requests as jrpc_client


class ErrorV1(xjsonrpc.exc.JsonRpcError):
    @classmethod
    def get_error_cls(cls, code, default):
        return next(iter((c for c in cls.__subclasses__() if getattr(c, 'code', None) == code)), default)


class PermissionDenied(ErrorV1):
    code = 1
    message = 'permission denied'


class ErrorV2(xjsonrpc.exc.JsonRpcError):
    @classmethod
    def get_error_cls(cls, code, default):
        return next(iter((c for c in cls.__subclasses__() if getattr(c, 'code', None) == code)), default)


class ResourceNotFound(ErrorV2):
    code = 1
    message = 'resource not found'


client_v1 = jrpc_client.Client('http://localhost:8080/api/v1', error_cls=ErrorV1)
client_v2 = jrpc_client.Client('http://localhost:8080/api/v2', error_cls=ErrorV2)

try:
    response: xjsonrpc.Response = client_v1.proxy.add_user(user={})
except PermissionDenied as e:
    print(e)

try:
    response: xjsonrpc.Response = client_v2.proxy.add_user(user={})
except ResourceNotFound as e:
    print(e)
