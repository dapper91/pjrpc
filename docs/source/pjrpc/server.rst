.. _server:

Server
======


``pjrpc`` supports popular backend frameworks like `aiohttp <https://aiohttp.readthedocs.io>`_,
`flask <https://flask.palletsprojects.com>`_ and message brokers like `aio_pika <https://aio-pika.readthedocs.io>`_.


Running of aiohttp based JSON-RPC server is a very simple process. Just define methods, add them to the
registry and run the server:

.. code-block:: python

    import uuid

    from aiohttp import web

    import pjrpc.server
    from pjrpc.server.integration import aiohttp

    methods = pjrpc.server.MethodRegistry()


    @methods.add(context='request')
    async def add_user(request: web.Request, user: dict) -> dict:
        user_id = uuid.uuid4().hex
        request.app['users'][user_id] = user

        return {'id': user_id, **user}


    jsonrpc_app = aiohttp.Application('/api/v1')
    jsonrpc_app.add_methods(methods)
    jsonrpc_app.app['users'] = {}

    if __name__ == "__main__":
        web.run_app(jsonrpc_app.http_app, host='localhost', port=8080)



API versioning
--------------

API versioning is a framework dependant feature but ``pjrpc`` has a full support for that.
Look at the following example illustrating how aiohttp JSON-RPC versioning is simple:

.. code-block:: python

    import uuid

    from aiohttp import web

    import pjrpc.server
    from pjrpc.server.integration import aiohttp

    methods_v1 = pjrpc.server.MethodRegistry()


    @methods_v1.add(context='request')
    async def add_user(request: web.Request, user: dict) -> dict:
        user_id = uuid.uuid4().hex
        request.config_dict['users'][user_id] = user

        return {'id': user_id, **user}


    methods_v2 = pjrpc.server.MethodRegistry()


    @methods_v2.add(context='request')
    async def add_user(request: web.Request, user: dict) -> dict:
        user_id = uuid.uuid4().hex
        request.config_dict['users'][user_id] = user

        return {'id': user_id, **user}


    app = web.Application()
    app['users'] = {}

    app_v1 = aiohttp.Application()
    app_v1.add_methods(methods_v1)
    app.add_subapp('/api/v1', app_v1)


    app_v2 = aiohttp.Application()
    app_v2.add_methods(methods_v2)
    app.add_subapp('/api/v2', app_v2)

    if __name__ == "__main__":
        web.run_app(app, host='localhost', port=8080)
