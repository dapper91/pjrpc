from aiohttp import client

from pjrpc.client import AbstractAsyncClient


class Client(AbstractAsyncClient):
    """
    `Aiohttp <https://aiohttp.readthedocs.io/en/stable/client.html>`_ library client backend.

    :param url: base url to be used as JSON-RPC endpoint
    :param session_args: additional :py:class:`aiohttp.ClientSession` arguments
    """

    def __init__(self, url, session_args=None, **kwargs):
        super().__init__(**kwargs)
        self._endpoint = url
        self._session = client.ClientSession(**(session_args or {}))

    async def _request(self, data, **kwargs):
        """
        Sends a JSON-RPC request.

        :param data: request text
        :returns: response text
        """

        kwargs = {
            'headers': {'Content-Type': 'application/json'},
            **kwargs
        }

        resp = await self._session.post(self._endpoint, data=data, **kwargs)
        resp.raise_for_status()

        return await resp.text()

    async def close(self):
        """
        Closes current http session.
        """

        await self._session.close()

    async def __aenter__(self):
        return self._session.__aenter__()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return self._session.__aexit__(exc_type, exc_val, exc_tb)
