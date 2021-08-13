.. _specification:

Specification:
==============


``pjrpc`` has built-in `OpenAPI <https://swagger.io/specification/>`_ and `OpenRPC <https://spec.open-rpc.org/#introduction>`_
specification generation support implemented by :py:class:`pjrpc.server.specs.openapi.OpenAPI`
and :py:class:`pjrpc.server.specs.openrpc.OpenRPC` respectively.
To enable schema generation you should pass specification generator instance to the JSON-RPC application.

.. code-block:: python

    json_rpc = integration.JsonRPC(
        '/api/v1',
        spec=specs.OpenAPI(
            info=specs.Info(version="1.0.0", title="User storage"),
            servers=[
                specs.Server(
                    url='http://127.0.0.1:8080',
                ),
            ],
            security_schemes=dict(
                basic=specs.SecurityScheme(
                    type=specs.SecuritySchemeType.HTTP,
                    scheme='basic',
                ),
            ),
            schema_extractor=extractors.pydantic.PydanticSchemaExtractor(),
            ui=specs.SwaggerUI(),
        ),
    )

OpenAPI specification will be available on ``/api/v1/openapi.json`` path. Path suffix can be overridden
by passing ``path`` parameter to a specification generator.

For more information about the specification see `OpenAPI Specification <https://swagger.io/specification/>`_.

OpenRPC specification generation looks pretty the same:

.. code-block:: python

    json_rpc = integration.JsonRPC(
        '/api/v1',
        spec=specs.OpenRPC(
            info=specs.Info(version="1.0.0", title="User storage"),
            servers=[
                specs.Server(
                    name='test',
                    url='http://127.0.0.1:8080/api/v1/',
                    summary='test server',
                ),
            ],
            schema_extractor=extractors.pydantic.PydanticSchemaExtractor(),
        ),
    )

OpenRPC specification will be available on ``/api/v1/openrpc.json`` path.


Method description, tags, errors, examples, parameters and return value schemas can be provided by hand
using :py:func:`pjrpc.server.specs.openapi.annotate` decorator or automatically extracted using schema extractor.
``pjrpc`` provides two schema extractors: :py:class:`pjrpc.server.specs.extractors.pydantic.PydanticSchemaExtractor`
and :py:class:`pjrpc.server.specs.extractors.docstring.DocstringSchemaExtractor`.
They uses `pydantic <https://pydantic-docs.helpmanual.io/>`_ models or python docstrings for method summary,
description, errors, examples and schema extraction respectively. You can implement your own schema extractor
inheriting it from :py:class:`pjrpc.server.specs.extractors.BaseSchemaExtractor` and implementing abstract methods.

.. code-block:: python

    @specs.annotate(
        tags=['users'],
        errors=[AlreadyExistsError],
        examples=[
            specs.MethodExample(
                summary="Simple example",
                params=dict(
                    user={
                        'name': 'Alex',
                        'surname': 'Smith',
                        'age': 25,
                    },
                ),
                result={
                    'id': 'c47726c6-a232-45f1-944f-60b98966ff1b',
                    'name': 'Alex',
                    'surname': 'Smith',
                    'age': 25,
                },
            ),
        ],
    )
    @methods.add
    @validator.validate
    def add_user(user: UserIn) -> UserOut:
        """
        Creates a user.

        :param object user: user data
        :return object: registered user
        :raise AlreadyExistsError: user already exists
        """

        for existing_user in flask.current_app.users_db.values():
            if user.name == existing_user.name:
                raise AlreadyExistsError()

        user_id = uuid.uuid4().hex
        flask.current_app.users_db[user_id] = user

        return UserOut(id=user_id, **user.dict())
