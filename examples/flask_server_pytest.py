import flask.testing
import pytest
import werkzeug.test

import pjrpc.server
from pjrpc.client.backend import requests as client
from pjrpc.client.integrations.pytest_requests import PjRpcRequestsMocker
from pjrpc.server.integration import flask as integration

methods = pjrpc.server.MethodRegistry()


@methods.add()
def div(a: int, b: int) -> float:
    return a / b


@pytest.fixture()
def http_app():
    return flask.Flask(__name__)


@pytest.fixture
def jsonrpc_app(http_app):
    json_rpc = integration.JsonRPC('/api/v1', http_app=http_app)
    json_rpc.add_methods(methods)

    return jsonrpc_app


class Response(werkzeug.test.Response):
    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception('client response error')

    @property
    def text(self):
        return self.data.decode()


@pytest.fixture()
def app_client(http_app):
    return flask.testing.FlaskClient(http_app, Response)


def test_pjrpc_server(http_app, jsonrpc_app, app_client):
    with PjRpcRequestsMocker(passthrough=True) as mocker:
        jsonrpc_cli = client.Client('/api/v1', session=app_client)

        mocker.add('http://127.0.0.2:8000/api/v1', 'div', result=2)
        result = jsonrpc_cli.proxy.div(4, 2)
        assert result == 2

        result = jsonrpc_cli.proxy.div(6, 2)
        assert result == 3
