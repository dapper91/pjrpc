.. _errors:

Errors
======


Errors handling
---------------

``pjrpc`` implements all the errors listed in `protocol specification <https://www.jsonrpc.org/specification#error_object>`_:

.. csv-table::
   :header: "code", "message", "meaning"
   :widths: 15, 15, 70

    -32700 , Parse error , Invalid JSON was received by the server. An error occurred on the server while parsing the JSON text.
    -32700 , Parse error , Invalid JSON was received by the server. An error occurred on the server while parsing the JSON text.
    -32600 , Invalid Request , The JSON sent is not a valid Request object.
    -32601 , Method not found , The method does not exist / is not available.
    -32602 , Invalid params , Invalid method parameter(s).
    -32603 , Internal error , Internal JSON-RPC error.
    -32000 to -32099 , Server error , Reserved for implementation-defined server-errors.


Errors can be found in ``pjrpc.common.exceptions`` module. Having said that error handling
is very simple and "pythonic-way":

.. code-block:: python

    import pjrpc
    from pjrpc.client.backend import requests as pjrpc_client

    client = pjrpc_client.Client('http://localhost/api/v1')

    try:
        result = client.proxy.sum(1, 2)
    except pjrpc.MethodNotFound as e:
        print(e)


Custom errors
-------------

Default error list may be easily extended. All you need to create an error class inherited from
``pjrpc.exc.JsonRpcError`` and define an error code and a description message. ``pjrpc`` will be automatically
deserializing custom errors for you:

.. code-block:: python

    import pjrpc
    from pjrpc.client.backend import requests as pjrpc_client

    class UserNotFound(pjrpc.exc.JsonRpcError):
        code = 1
        message = 'user not found'


    client = pjrpc_client.Client('http://localhost/api/v1')

    try:
        result = client.proxy.get_user(user_id=1)
    except UserNotFound as e:
        print(e)


Server side
-----------

On the server side everything is pretty straightforward:

.. code-block:: python

    import uuid

    import flask

    import pjrpc
    from pjrpc.server import MethodRegistry
    from pjrpc.server.integration import flask as integration

    app = flask.Flask(__name__)

    methods = pjrpc.server.MethodRegistry()


    class UserNotFound(pjrpc.exc.JsonRpcError):
        code = 1
        message = 'user not found'

    @methods.add
    def add_user(user: dict):
        user_id = uuid.uuid4().hex
        flask.current_app.users[user_id] = user

        return {'id': user_id, **user}

     def get_user(self, user_id: str):
        user = flask.current_app.users.get(user_id)
        if not user:
            raise UserNotFound(data=user_id)

        return user


    json_rpc = integration.JsonRPC('/api/v1')
    json_rpc.dispatcher.add_methods(methods)

    app.users = {}

    json_rpc.init_app(app)

    if __name__ == "__main__":
        app.run(port=80)


Independent clients errors
--------------------------

Having multiple JSON-RPC services with overlapping error codes is a "real-world" case everyone has ever dialed with.
To handle such situation client has an `error_cls` argument to set a base error class for a particular client:

.. code-block:: python

    import pjrpc
    from pjrpc.client.backend import requests as jrpc_client


    class ErrorV1(pjrpc.exc.JsonRpcError):
        @classmethod
        def get_error_cls(cls, code, default):
            return next(iter((c for c in cls.__subclasses__() if getattr(c, 'code', None) == code)), default)


    class PermissionDenied(ErrorV1):
        code = 1
        message = 'permission denied'


    class ErrorV2(pjrpc.exc.JsonRpcError):
        @classmethod
        def get_error_cls(cls, code, default):
            return next(iter((c for c in cls.__subclasses__() if getattr(c, 'code', None) == code)), default)


    class ResourceNotFound(ErrorV2):
        code = 1
        message = 'resource not found'


    client_v1 = jrpc_client.Client('http://localhost:8080/api/v1', error_cls=ErrorV1)
    client_v2 = jrpc_client.Client('http://localhost:8080/api/v2', error_cls=ErrorV2)

    try:
        response: pjrpc.Response = client_v1.proxy.add_user(user={})
    except PermissionDenied as e:
        print(e)

    try:
        response: pjrpc.Response = client_v2.proxy.add_user(user={})
    except ResourceNotFound as e:
        print(e)

The above snippet illustrates two clients receiving the same error code however each one has its own semantic
and therefore its own exception class. Nevertheless clients raise theirs own exceptions for the same error code.
