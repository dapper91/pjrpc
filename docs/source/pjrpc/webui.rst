.. _webui:

Web UI
======

``pjrpc`` supports integrated web UI as an extra dependency. Three UI types are supported:

- SwaggerUI (`<https://swagger.io/tools/swagger-ui/>`_)
- RapiDoc (`<https://mrin9.github.io/RapiDoc/>`_)
- ReDoc (`<https://github.com/Redocly/redoc>`_)

Web UI extra dependency can be installed using the following code:

.. code-block:: console

    $ pip install pjrpc[openapi-ui-bundles]


The following example illustrates how to configure specification generation and Swagger UI web tool with basic auth
using flask web framework:

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
        """
        Creates a user.

        :param request: http request
        :param object user: user data
        :return object: registered user
        :raise AlreadyExistsError: user already exists
        """

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
        """
        Returns a user.

        :param request: http request
        :param object user_id: user id
        :return object: registered user
        :raise NotFoundError: user not found
        """

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
        """
        Deletes a user.

        :param request: http request
        :param object user_id: user id
        :raise NotFoundError: user not found
        """

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



Specification is available on http://localhost:8080/rpc/api/openapi.json

Web UI is running on http://localhost:8080/rpc/api/v1/swagger/ and http://localhost:8080/rpc/api/v1/redoc/

Swagger UI
~~~~~~~~~~

.. image:: ../_static/swagger-ui-screenshot.png
  :width: 1024
  :alt: OpenAPI full example

RapiDoc
~~~~~~~

.. image:: ../_static/rapidoc-screenshot.png
  :width: 1024
  :alt: OpenAPI cli example

ReDoc
~~~~~

.. image:: ../_static/redoc-screenshot.png
  :width: 1024
  :alt: OpenAPI method example
