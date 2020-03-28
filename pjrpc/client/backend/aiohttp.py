from typing import Any, Dict, Optional
from aiohttp import client

import pjrpc
from pjrpc.client import AbstractAsyncClient


class Client(AbstractAsyncClient):
    """
    `Aiohttp <https://aiohttp.readthedocs.io/en/stable/client.html>`_ library client backend.

    :param url: url to be used as JSON-RPC endpoint
    :param session_args: additional :py:class:`aiohttp.ClientSession` arguments
    :param session: custom session to be used instead of :py:class:`aiohttp.ClientSession`
    """

    def __init__(
        self, url: str,
        session_args: Optional[Dict[str, Any]] = None,
        session: Optional[client.ClientSession] = None,
        **kwargs: Any,
    ):
        super().__init__(**kwargs)
        self._endpoint = url
        self._session = session or client.ClientSession(**(session_args or {}))

    async def _request(self, request_text: str, is_notification: bool = False, **kwargs: Any) -> Optional[str]:
        """
        Sends a JSON-RPC request.

        :param data: request text
        :param is_notification: is the request a notification
        :returns: response text
        """

        kwargs = {
            'headers': {'Content-Type': 'application/json'},
            **kwargs,
        }

        resp = await self._session.post(self._endpoint, data=request_text, **kwargs)
        resp.raise_for_status()

        response_text = await resp.text()
        if is_notification:
            return None

        content_type = resp.headers.get('Content-Type', '')
        if response_text and content_type.split(';')[0] != 'application/json':
            raise pjrpc.exc.DeserializationError(f"unexpected response content type: {content_type}")

        return response_text

    async def close(self) -> None:
        """
        Closes current http session.
        """

        await self._session.close()

    async def __aenter__(self) -> 'Client':
        await self._session.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self._session.__aexit__(exc_type, exc_val, exc_tb)
