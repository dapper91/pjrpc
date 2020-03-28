from typing import Any, Optional
import requests

import pjrpc
from pjrpc.client import AbstractClient


class Client(AbstractClient):
    """
    `Requests <https://2.python-requests.org/>`_ library client backend.

    :param url: url to be used as JSON-RPC endpoint.
    :param session: custom session to be used instead of :py:class:`requests.Session`
    :param kwargs: parameters to be passed to :py:class:`pjrpc.client.AbstractClient`
    """

    def __init__(self, url: str, session: Optional[requests.Session] = None, **kwargs: Any):
        super().__init__(**kwargs)
        self._endpoint = url
        self._session = session or requests.Session()

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

        resp = self._session.post(self._endpoint, data=request_text, **kwargs)
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

        self._session.close()

    def __enter__(self) -> 'Client':
        self._session.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self._session.__exit__(exc_type, exc_val, exc_tb)
