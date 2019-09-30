import requests

from pjrpc.client import AbstractClient


class Client(AbstractClient):
    """
    `Requests <https://2.python-requests.org/>`_ library client backend.

    :param url: base url to be used as JSON-RPC endpoint.
    :param kwargs: parameters to be passed to :py:class:`pjrpc.client.AbstractClient`
    """

    def __init__(self, url, **kwargs):
        super().__init__(**kwargs)
        self._endpoint = url
        self._session = requests.Session()

    def _request(self, data, **kwargs):
        """
        Sends a JSON-RPC request.

        :param data: request text
        :returns: response text
        """

        kwargs = {
            'headers': {'Content-Type': 'application/json'},
            **kwargs
        }

        resp = self._session.post(self._endpoint, data=data, **kwargs)
        resp.raise_for_status()

        return resp.text

    def close(self):
        """
        Closes the current http session.
        """

        self._session.close()

    def __enter__(self):
        return self._session.__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self._session.__exit__(exc_type, exc_val, exc_tb)
