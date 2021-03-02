from typing import Any, List, Optional
import httpx

import pjrpc
from pjrpc.client import AbstractClient, AbstractAsyncClient


class Client(AbstractClient):
    """
    `httpx <https://www.python-httpx.org/>`_ library sync client backend.

    :param url: url to be used as JSON-RPC endpoint.
    :param session: custom session to be used instead of :py:class:`requests.Session`
    :param kwargs: parameters to be passed to :py:class:`pjrpc.client.AbstractClient`
    """

    def __init__(self, url: str, client: Optional[httpx.Client] = None, **kwargs: Any):
        super().__init__(**kwargs)
        self._endpoint = url
        self._client = client or httpx.Client()

    def _request(self, request_text: str, is_notification: bool = False, **kwargs: Any) -> Optional[str]:
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

        resp = self._client.post(self._endpoint, content=request_text, **kwargs)
        resp.raise_for_status()
        if is_notification:
            return None

        response_text = resp.text
        content_type = resp.headers.get('Content-Type', '')
        if response_text and content_type.split(';')[0] != 'application/json':
            raise pjrpc.exc.DeserializationError(f"unexpected response content type: {content_type}")

        return response_text

    def close(self) -> None:
        """
        Closes the current http session.
        """

        self._client.close()

    def __enter__(self) -> 'Client':
        self._client.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self._client.__exit__(exc_type, exc_val, exc_tb)


class AsyncClient(AbstractAsyncClient):
    """
    `httpx <https://www.python-httpx.org/>`_ library async client backend.

    :param url: url to be used as JSON-RPC endpoint
    :param session_args: additional :py:class:`aiohttp.ClientSession` arguments
    :param session: custom session to be used instead of :py:class:`aiohttp.ClientSession`
    """

    def __init__(self, url: str, client: Optional[httpx.AsyncClient] = None, **kwargs: Any):
        super().__init__(**kwargs)
        self._endpoint = url
        self._client = client or httpx.AsyncClient()

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

        resp = await self._client.post(self._endpoint, content=request_text, **kwargs)
        resp.raise_for_status()

        response_buff: List[str] = []
        async for chunk in resp.aiter_text():
            response_buff.append(chunk)

        response_text = ''.join(response_buff)
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

        await self._client.aclose()

    async def __aenter__(self) -> 'AsyncClient':
        await self._client.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self._client.__aexit__(exc_type, exc_val, exc_tb)
