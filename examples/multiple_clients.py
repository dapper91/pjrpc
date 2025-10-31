from typing import ClassVar

import pjrpc
from pjrpc.client.backend import requests as jrpc_client


class ErrorV1(pjrpc.client.exceptions.TypedError, base=True):
    pass


class PermissionDenied(ErrorV1):
    CODE: ClassVar[int] = 1
    MESSAGE: ClassVar[str] = 'permission denied'


class ErrorV2(pjrpc.client.exceptions.TypedError, base=True):
    pass


class ResourceNotFound(ErrorV2):
    CODE: ClassVar[int] = 1
    MESSAGE: ClassVar[str] = 'resource not found'


client_v1 = jrpc_client.Client('http://localhost:8080/api/v1', error_cls=ErrorV1)
client_v2 = jrpc_client.Client('http://localhost:8080/api/v2', error_cls=ErrorV2)

try:
    client_v1.proxy.add_user(user={})
except PermissionDenied as e:
    print(e)

try:
    client_v2.proxy.add_user(user={})
except ResourceNotFound as e:
    print(e)
