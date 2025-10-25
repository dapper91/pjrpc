from pjrpc import client
from pjrpc.common import Response


def test_request_middleware(mocker):
    middleware_mock = mocker.stub()

    class Client(client.AbstractClient):
        def _request(self, *args, **kwargs):
            pass

    def middleware(request, request_kwargs, /, handler):
        middleware_mock()
        return Response(result=None)

    cli = Client(middlewares=[middleware])
    cli.call("test")

    assert middleware_mock.call_count == 1


async def test_async_request_middleware(mocker):
    middleware_mock = mocker.stub()

    class Client(client.AbstractAsyncClient):
        async def _request(self, *args, **kwargs):
            pass

    async def middleware(request, request_kwargs, /, handler):
        middleware_mock()
        return Response(result=None)

    cli = Client(middlewares=[middleware])
    await cli.call("test")

    assert middleware_mock.call_count == 1
