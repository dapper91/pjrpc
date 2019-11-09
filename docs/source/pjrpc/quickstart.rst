.. _quickstart:

Quick start
===========


The way of using ``pjrpc`` clients is very simple and intuitive. Methods may be called by name, using proxy object
or by sending handmade ``pjrpc.Request`` class object. Of course, the request class can be easily inherited
and adapted to your needs. Notification requests also supported.

.. code-block:: python

    import pjrpc
    from pjrpc.client.backend import requests as pjrpc_client


    client = pjrpc_client.Client('http://localhost/api/v1')

    response: pjrpc.Response = client.send(pjrpc.Request('sum', params=[1, 2]))
    print(f"1 + 2 = {response.result}")

    result = client('sum', a=1, b=2)
    print(f"1 + 2 = {result}")

    result = client.proxy.sum(1, 2)
    print(f"1 + 2 = {result}")

    client.notify('tick')


Asynchronous client api looks pretty much the same:

.. code-block:: python

    import pjrpc
    from pjrpc.client.backend import aiohttp as pjrpc_client


    client = pjrpc_client.Client('http://localhost/api/v1')

    response = await client.send(pjrpc.Request('sum', params=[1, 2], id=1))
    print(f"1 + 2 = {response.result}")

    result = await client('sum', a=1, b=2)
    print(f"1 + 2 = {result}")

    result = await client.proxy.sum(1, 2)
    print(f"1 + 2 = {result}")

    await client.notify('tick')


``pjrpc`` supports popular backend frameworks like `aiohttp <https://aiohttp.readthedocs.io>`_,
`flask <https://flask.palletsprojects.com>`_ and message brokers like `kombu <https://kombu.readthedocs.io/en/stable/>`_
and `aio_pika <https://aio-pika.readthedocs.io>`_.


Running of aiohttp based JSON-RPC server is a very simple process. Just define methods, add them to the
registry and run the server:

.. code-block:: python

    import uuid

    from aiohttp import web

    import pjrpc.server
    from pjrpc.server.integration import aiohttp

    methods = pjrpc.server.MethodRegistry()


    @methods.add(context='request')
    async def add_user(request: web.Request, user: dict):
        user_id = uuid.uuid4().hex
        request.app['users'][user_id] = user

        return {'id': user_id, **user}


    app = aiohttp.Application('/api/v1')
    app.dispatcher.add_methods(methods)
    app['users'] = {}

    if __name__ == "__main__":
        web.run_app(app, host='localhost', port=8080)


Very often besides dumb method parameters validation you need to implement more "deep" validation and provide
comprehensive errors description to your clients. Fortunately ``pjrpc`` has builtin parameter validation based on
`pydantic <https://pydantic-docs.helpmanual.io/>`_ library which uses python type annotation based validation.
Look at the following example. All you need to annotate method parameters (or describe more complex type if necessary),
that's it. ``pjrpc`` will be validating method parameters and returning informative errors to clients:


.. code-block:: python

    import enum
    import uuid
    from typing import List

    import pydantic
    from aiohttp import web

    import pjrpc.server
    from pjrpc.server.validators import pydantic as validators
    from pjrpc.server.integration import aiohttp

    methods = pjrpc.server.MethodRegistry()
    validator = validators.PydanticValidator()


    class ContactType(enum.Enum):
        PHONE = 'phone'
        EMAIL = 'email'


    class Contact(pydantic.BaseModel):
        type: ContactType
        value: str


    class User(pydantic.BaseModel):
        name: str
        surname: str
        age: int
        contacts: List[Contact]


    @methods.add(context='request')
    @validator.validate
    async def add_user(request: web.Request, user: User):
        user_id = uuid.uuid4()
        request.app['users'][user_id] = user

        return {'id': user_id, **user.dict()}


    class JSONEncoder(pjrpc.common.JSONEncoder):

        def default(self, o):
            if isinstance(o, uuid.UUID):
                return o.hex
            if isinstance(o, enum.Enum):
                return o.value

            return super().default(o)


    app = aiohttp.Application('/api/v1', json_encoder=JSONEncoder)
    app.dispatcher.add_methods(methods)
    app['users'] = {}

    if __name__ == "__main__":
        web.run_app(app, host='localhost', port=8080)
