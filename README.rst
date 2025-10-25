=====
pjrpc
=====

.. image:: https://static.pepy.tech/personalized-badge/pjrpc?period=month&units=international_system&left_color=grey&right_color=orange&left_text=Downloads/month
    :target: https://pepy.tech/project/pjrpc
    :alt: Downloads/month
.. image:: https://github.com/dapper91/pjrpc/actions/workflows/test.yml/badge.svg?branch=master
    :target: https://github.com/dapper91/pjrpc/actions/workflows/test.yml
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

- framework agnostic
- intuitive api
- extendability
- synchronous and asynchronous client backed
- synchronous and asynchronous server support
- popular frameworks integration
- builtin parameter validation
- pytest integration
- openapi schema generation support
- web ui support (SwaggerUI, RapiDoc, ReDoc)

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
- `pydantic <https://pydantic-docs.helpmanual.io/>`_
- `requests <https://requests.readthedocs.io>`_
- `httpx <https://www.python-httpx.org/>`_
- `openapi-ui-bundles <https://github.com/dapper91/python-openapi-ui-bundles>`_


Documentation
-------------

Documentation is available at `Read the Docs <https://pjrpc.readthedocs.io>`_.


Quickstart
----------

Client requests
_______________

``pjrpc`` client interface is very simple and intuitive. Methods may be called by name, using proxy object
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

    with client.batch() as batch:
        batch.send(pjrpc.Request('sum', [2, 2], id=1))
        batch.send(pjrpc.Request('sub', [2, 2], id=2))
        batch.send(pjrpc.Request('div', [2, 2], id=3))
        batch.send(pjrpc.Request('mult', [2, 2], id=4))

    batch_response = batch.get_response()

    print(f"2 + 2 = {batch_response[0].result}")
    print(f"2 - 2 = {batch_response[1].result}")
    print(f"2 / 2 = {batch_response[2].result}")
    print(f"2 * 2 = {batch_response[3].result}")


There are also several alternative approaches which are a syntactic sugar for the first one (note that the result
is not a ``pjrpc.common.BatchResponse`` object anymore but a tuple of "plain" method invocation results):

- using call notation:

.. code-block:: python

    async with client.batch() as batch:
        batch('sum', 2, 2)
        batch('sub', 2, 2)
        batch('div', 2, 2)
        batch('mult', 2, 2)

    result = batch.get_results()

    print(f"2 + 2 = {result[0]}")
    print(f"2 - 2 = {result[1]}")
    print(f"2 / 2 = {result[2]}")
    print(f"2 * 2 = {result[3]}")


- using proxy call:

.. code-block:: python

    async with client.batch() as batch:
        batch.proxy.sum(2, 2)
        batch.proxy.sub(2, 2)
        batch.proxy.div(2, 2)
        batch.proxy.mult(2, 2)

    result = batch.get_results()

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

    batch_response = client.send(
        pjrpc.BatchRequest(
            pjrpc.Request('sum', [2, 2], id=1),
            pjrpc.Request('sub', [2, 2], id=2),
            pjrpc.Request('div', [2, 2], id=3),
            pjrpc.Request('mult', [2, 2], id=4),
        )
    )

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

    with client.batch() as batch:
        batch.notify('tick')
        batch.notify('tack')
        batch.notify('tick')
        batch.notify('tack')



Server
______

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


    @methods.add(pass_context='request')
    async def add_user(request: web.Request, user: dict) -> dict:
        user_id = uuid.uuid4().hex
        request.app['users'][user_id] = user

        return {'id': user_id, **user}


    jsonrpc_app = aiohttp.Application('/api/v1')
    jsonrpc_app.add_methods(methods)
    jsonrpc_app.app['users'] = {}

    if __name__ == "__main__":
        web.run_app(jsonrpc_app.http_app, host='localhost', port=8080)


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

    import pydantic
    from aiohttp import web

    import pjrpc.server
    from pjrpc.server.validators import pydantic as validators
    from pjrpc.server.integration import aiohttp

    methods = pjrpc.server.MethodRegistry(
        validator_factory=validators.PydanticValidatorFactory(exclude=aiohttp.is_aiohttp_request),
    )

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
        contacts: list[Contact]


    @methods.add(pass_context='request')
    async def add_user(request: web.Request, user: User):
        user_id = uuid.uuid4()
        request.app['users'][user_id] = user

        return {'id': user_id, **user.dict()}


    class JSONEncoder(pjrpc.server.JSONEncoder):
        def default(self, o):
            if isinstance(o, uuid.UUID):
                return o.hex
            if isinstance(o, enum.Enum):
                return o.value

            return super().default(o)


    jsonrpc_app = aiohttp.Application('/api/v1', json_encoder=JSONEncoder)
    jsonrpc_app.add_methods(methods)
    jsonrpc_app.http_app['users'] = {}

    if __name__ == "__main__":
        web.run_app(jsonrpc_app.http_app, host='localhost', port=8080)


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
``pjrpc.exc.TypedError`` and define an error code and a description message. ``pjrpc`` will be automatically
deserializing custom errors for you:

.. code-block:: python

    import pjrpc
    from pjrpc.client.backend import requests as pjrpc_client

    class UserNotFound(pjrpc.exc.TypedError):
        CODE = 1
        MESSAGE = 'user not found'


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

    methods = pjrpc.server.MethodRegistry()


    class UserNotFound(pjrpc.exc.TypedError):
        CODE = 1
        MESSAGE = 'user not found'


    @methods.add()
    def add_user(user: dict) -> dict:
        user_id = uuid.uuid4().hex
        flask.current_app.users[user_id] = user

        return {'id': user_id, **user}

    @methods.add()
    def get_user(user_id: str) -> dict:
        user = flask.current_app.users.get(user_id)
        if not user:
            raise UserNotFound(data=user_id)

        return user


    json_rpc = integration.JsonRPC('/api/v1')
    json_rpc.add_methods(methods)

    json_rpc.http_app.users = {}

    if __name__ == "__main__":
        json_rpc.http_app.run(port=80)



Open API specification
______________________

``pjrpc`` has built-in `OpenAPI <https://swagger.io/specification/>`_ and `OpenRPC <https://spec.open-rpc.org/#introduction>`_
specification generation support and integrated web UI as an extra dependency. Three UI types are supported:

- SwaggerUI (`<https://swagger.io/tools/swagger-ui/>`_)
- RapiDoc (`<https://mrin9.github.io/RapiDoc/>`_)
- ReDoc (`<https://github.com/Redocly/redoc>`_)

Web UI extra dependency can be installed using the following code:

.. code-block:: console

    $ pip install pjrpc[openapi-ui-bundles]

The following example illustrates how to configure OpenAPI specification generation
and Swagger UI web tool with basic auth:

.. code-block:: python

    import uuid
    from typing import Annotated, Any

    import aiohttp.typedefs
    import pydantic as pd
    from aiohttp import web

    import pjrpc.server.specs.extractors.pydantic
    import pjrpc.server.specs.openapi.ui
    from pjrpc.server.integration import aiohttp as integration
    from pjrpc.server.specs import extractors
    from pjrpc.server.specs import openapi as specs
    from pjrpc.server.validators import pydantic as validators


    methods = pjrpc.server.MethodRegistry(
        validator_factory=validators.PydanticValidatorFactory(exclude=integration.is_aiohttp_request),
        metadata_processors=[
            specs.MethodSpecificationGenerator(
                extractor=extractors.pydantic.PydanticMethodInfoExtractor(
                    exclude=integration.is_aiohttp_request,
                ),
            ),
        ],
    )


    UserName = Annotated[
        str,
        pd.Field(description="User name", examples=["John"]),
    ]

    UserSurname = Annotated[
        str,
        pd.Field(description="User surname", examples=['Doe']),
    ]

    UserAge = Annotated[
        int,
        pd.Field(description="User age", examples=[36]),
    ]

    UserId = Annotated[
        uuid.UUID,
        pd.Field(description="User identifier", examples=["226a2c23-c98b-4729-b398-0dae550e99ff"]),
    ]


    class UserIn(pd.BaseModel):
        """
        User registration data.
        """

        name: UserName
        surname: UserSurname
        age: UserAge


    class UserOut(UserIn):
        """
        Registered user data.
        """

        id: UserId


    class AlreadyExistsError(pjrpc.exc.TypedError):
        """
        User already registered error.
        """

        CODE = 2001
        MESSAGE = "user already exists"


    class NotFoundError(pjrpc.exc.TypedError):
        """
        User not found error.
        """

        CODE = 2002
        MESSAGE = "user not found"


    @methods.add(
        pass_context='request',
        metadata=[
            specs.metadata(
                summary='Creates a user',
                tags=['users'],
                errors=[AlreadyExistsError],
            ),
        ],
    )
    def add_user(request: web.Request, user: UserIn) -> UserOut:
        for existing_user in request.config_dict['users'].values():
            if user.name == existing_user.name:
                raise AlreadyExistsError()

        user_id = uuid.uuid4()
        request.config_dict['users'][user_id] = user

        return UserOut(id=user_id, **user.model_dump())


    @methods.add(
        pass_context='request',
        metadata=[
            specs.metadata(
                summary='Returns a user',
                tags=['users'],
                errors=[NotFoundError],
            ),
        ],
    )
    def get_user(request: web.Request, user_id: UserId) -> UserOut:
        user = request.config_dict['users'].get(user_id.hex)
        if not user:
            raise NotFoundError()

        return UserOut(id=user_id, **user.model_dump())


    @methods.add(
        pass_context='request',
        metadata=[
            specs.metadata(
                summary='Deletes a user',
                tags=['users'],
                errors=[NotFoundError],
            ),
        ],
    )
    def delete_user(request: web.Request, user_id: UserId) -> None:
        user = request.config_dict['users'].pop(user_id.hex, None)
        if not user:
            raise NotFoundError()


    class JSONEncoder(pjrpc.server.JSONEncoder):
        def default(self, o: Any) -> Any:
            if isinstance(o, pd.BaseModel):
                return o.model_dump()
            if isinstance(o, uuid.UUID):
                return str(o)

            return super().default(o)


    openapi_spec = specs.OpenAPI(
        info=specs.Info(version="1.0.0", title="User storage"),
        servers=[
            specs.Server(
                url='http://127.0.0.1:8080',
            ),
        ],
        security_schemes=dict(
            basicAuth=specs.SecurityScheme(
                type=specs.SecuritySchemeType.HTTP,
                scheme='basic',
            ),
        ),
        security=[
            dict(basicAuth=[]),
        ],
    )

    http_app = web.Application()
    http_app['users'] = {}

    jsonrpc_app = integration.Application('/api')
    jsonrpc_app.add_spec(openapi_spec, path='openapi.json')
    jsonrpc_app.add_spec_ui('swagger', specs.ui.SwaggerUI(), spec_url='../openapi.json')
    jsonrpc_app.add_spec_ui('redoc', specs.ui.ReDoc(), spec_url='../openapi.json')

    jsonrpc_v1_app = integration.Application(http_app=web.Application(), json_encoder=JSONEncoder)
    jsonrpc_v1_app.add_methods(methods)

    jsonrpc_app.add_subapp('/v1', jsonrpc_v1_app)
    http_app.add_subapp('/rpc', jsonrpc_app.http_app)


    if __name__ == "__main__":
        web.run_app(http_app, host='localhost', port=8080)



Specification is available on http://localhost:8080/rpc/api/v1/openapi.json

Web UI is running on http://localhost:8080/rpc/api/v1/swagger/ and http://localhost:8080/rpc/api/v1/redoc/

Swagger UI:
~~~~~~~~~~~

.. image:: docs/source/_static/swagger-ui-screenshot.png
  :width: 1024
  :alt: Open API full example

RapiDoc:
~~~~~~~~

.. image:: docs/source/_static/rapidoc-screenshot.png
  :width: 1024
  :alt: Open API cli example

Redoc:
~~~~~~

.. image:: docs/source/_static/redoc-screenshot.png
  :width: 1024
  :alt: Open API method example
