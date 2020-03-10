=====
pjrpc
=====

.. image:: https://travis-ci.org/dapper91/pjrpc.svg?branch=master
    :target: https://travis-ci.org/dapper91/pjrpc
    :alt: Build status
.. image:: https://img.shields.io/pypi/l/pjrpc.svg
    :target: https://pypi.org/project/pjrpc
    :alt: License
.. image:: https://img.shields.io/pypi/pyversions/pjrpc.svg
    :target: https://pypi.org/project/pjrpc
    :alt: Supported Python versions
.. image:: https://codecov.io/gh/dapper91/pjrpc/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/dapper91/pjrpc
    :alt: Code coverage
.. image:: https://readthedocs.org/projects/pjrpc/badge/?version=stable&style=flat
   :alt: ReadTheDocs status
   :target: https://pjrpc.readthedocs.io/en/stable/


``pjrpc`` is an extensible `JSON-RPC <https://www.jsonrpc.org>`_ client/server library with an intuitive interface
that can be easily extended and integrated in your project without writing a lot of boilerplate code.

Features:

- intuitive api
- extendability
- synchronous and asynchronous client backed
- popular frameworks integration
- builtin parameter validation
- pytest integration

Installation
------------

You can install pjrpc with pip:

.. code-block:: console

    $ pip install pjrpc


Extra requirements
------------------

- `aiohttp <https://aiohttp.readthedocs.io>`_
- `aio_pika <https://aio-pika.readthedocs.io>`_
- `flask <https://flask.palletsprojects.com>`_
- `jsonschema <https://python-jsonschema.readthedocs.io>`_
- `kombu <https://kombu.readthedocs.io/en/stable/>`_
- `pydantic <https://pydantic-docs.helpmanual.io/>`_
- `requests <https://requests.readthedocs.io>`_


Documentation
-------------

Documentation is available at `Read the Docs <https://pjrpc.readthedocs.io/en/latest/>`_.


Quickstart
----------

Client requests
_______________

The way of using ``pjrpc`` clients is very simple and intuitive. Methods may be called by name, using proxy object
or by sending handmade ``pjrpc.common.Request`` class object. Notification requests can be made using
``pjrpc.client.AbstractClient.notify`` method or by sending a ``pjrpc.common.Request`` object without id.

.. code-block:: python

    import pjrpc
    from pjrpc.client.backend import requests as pjrpc_client


    client = pjrpc_client.Client('http://localhost/api/v1')

    response: pjrpc.Response = client.send(pjrpc.Request('sum', params=[1, 2], id=1))
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


Batch requests
______________

Batch requests also supported. You can build ``pjrpc.common.BatchRequest`` request by your hand and then send it to the
server. The result is a ``pjrpc.common.BatchResponse`` instance you can iterate over to get all the results or get
each one by index:

.. code-block:: python

    import pjrpc
    from pjrpc.client.backend import requests as pjrpc_client


    client = pjrpc_client.Client('http://localhost/api/v1')

    batch_response = await client.batch.send(pjrpc.BatchRequest(
        pjrpc.Request('sum', [2, 2], id=1),
        pjrpc.Request('sub', [2, 2], id=2),
        pjrpc.Request('div', [2, 2], id=3),
        pjrpc.Request('mult', [2, 2], id=4),
    ))
    print(f"2 + 2 = {batch_response[0].result}")
    print(f"2 - 2 = {batch_response[1].result}")
    print(f"2 / 2 = {batch_response[2].result}")
    print(f"2 * 2 = {batch_response[3].result}")


There are also several alternative approaches which are a syntactic sugar for the first one (note that the result
is not a ``pjrpc.common.BatchResponse`` object anymore but a tuple of "plain" method invocation results):

- using chain call notation:

.. code-block:: python

    result = await client.batch('sum', 2, 2)('sub', 2, 2)('div', 2, 2)('mult', 2, 2).call()
    print(f"2 + 2 = {result[0]}")
    print(f"2 - 2 = {result[1]}")
    print(f"2 / 2 = {result[2]}")
    print(f"2 * 2 = {result[3]}")


- using subscription operator:

.. code-block:: python

    result = await client.batch[
        ('sum', 2, 2),
        ('sub', 2, 2),
        ('div', 2, 2),
        ('mult', 2, 2),
    ]
    print(f"2 + 2 = {result[0]}")
    print(f"2 - 2 = {result[1]}")
    print(f"2 / 2 = {result[2]}")
    print(f"2 * 2 = {result[3]}")


- using proxy chain call:

.. code-block:: python

    result = await client.batch.proxy.sum(2, 2).sub(2, 2).div(2, 2).mult(2, 2).call()
    print(f"2 + 2 = {result[0]}")
    print(f"2 - 2 = {result[1]}")
    print(f"2 / 2 = {result[2]}")
    print(f"2 * 2 = {result[3]}")


Which one to use is up to you but be aware that if any of the requests returns an error the result of the other ones
will be lost. In such case the first approach can be used to iterate over all the responses and get the results of
the succeeded ones like this:

.. code-block:: python

    import pjrpc
    from pjrpc.client.backend import requests as pjrpc_client


    client = pjrpc_client.Client('http://localhost/api/v1')

    batch_response = client.batch.send(pjrpc.BatchRequest(
        pjrpc.Request('sum', [2, 2], id=1),
        pjrpc.Request('sub', [2, 2], id=2),
        pjrpc.Request('div', [2, 2], id=3),
        pjrpc.Request('mult', [2, 2], id=4),
    ))

    for response in batch_response:
        if response.is_success:
            print(response.result)
        else:
            print(response.error)


Batch notifications:

.. code-block:: python

    import pjrpc
    from pjrpc.client.backend import requests as pjrpc_client


    client = pjrpc_client.Client('http://localhost/api/v1')

    client.batch.notify('tick').notify('tack').notify('tick').notify('tack').call()



Server
______

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


    jsonrpc_app = aiohttp.Application('/api/v1')
    jsonrpc_app.dispatcher.add_methods(methods)
    jsonrpc_app.app['users'] = {}

    if __name__ == "__main__":
        web.run_app(jsonrpc_app.app, host='localhost', port=8080)


Parameter validation
____________________

Very often besides dumb method parameters validation it is necessary to implement more "deep" validation and provide
comprehensive errors description to clients. Fortunately ``pjrpc`` has builtin parameter validation based on
`pydantic <https://pydantic-docs.helpmanual.io/>`_ library which uses python type annotation for validation.
Look at the following example: all you need to annotate method parameters (or describe more complex types beforehand if
necessary). ``pjrpc`` will be validating method parameters and returning informative errors to clients.


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


    jsonrpc_app = aiohttp.Application('/api/v1', json_encoder=JSONEncoder)
    jsonrpc_app.dispatcher.add_methods(methods)
    jsonrpc_app.app['users'] = {}

    if __name__ == "__main__":
        web.run_app(jsonrpc_app.app, host='localhost', port=8080)


Error handling
______________

``pjrpc`` implements all the errors listed in `protocol specification <https://www.jsonrpc.org/specification#error_object>`_
which can be found in ``pjrpc.common.exceptions`` module so that error handling is very simple and "pythonic-way":

.. code-block:: python

    import pjrpc
    from pjrpc.client.backend import requests as pjrpc_client

    client = pjrpc_client.Client('http://localhost/api/v1')

    try:
        result = client.proxy.sum(1, 2)
    except pjrpc.MethodNotFound as e:
        print(e)


Default error list can be easily extended. All you need to create an error class inherited from
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


On the server side everything is also pretty straightforward:

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

    @methods.add
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
