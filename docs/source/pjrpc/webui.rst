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


To enable Web UI pass :py:class:`pjrpc.server.specs.openapi.SwaggerUI`, :py:class:`pjrpc.server.specs.openapi.RapiDoc` or
:py:class:`pjrpc.server.specs.openapi.ReDoc` to a specification generator as a ``ui`` parameter.
Web UI will be available at ``/ui/`` path.
It can be overridden by passing ``ui_path`` parameter to the specification generator.

.. code-block:: python

    json_rpc = AuthenticatedJsonRPC(
        '/api/v1',
        json_encoder=JSONEncoder,
        spec=specs.OpenAPI(
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
                dict(basicAuth=[])
            ],
            schema_extractor=extractors.pydantic.PydanticSchemaExtractor(),
            ui=specs.SwaggerUI(),
        ),
    )


The following example illustrates how to configure specification generation and Swagger UI web tool with basic auth
using flask web framework:

.. code-block:: python

    import uuid
    from typing import Annotated, Any, Optional

    import flask
    import flask_cors
    import flask_httpauth
    import pydantic as pd
    from werkzeug import security

    import pjrpc.server.specs.extractors.pydantic
    from pjrpc.server.integration import flask as integration
    from pjrpc.server.specs import extractors
    from pjrpc.server.specs import openapi as specs
    from pjrpc.server.validators import pydantic as validators

    app = flask.Flask('myapp')
    flask_cors.CORS(app, resources={"/myapp/api/v1/*": {"origins": "*"}})

    methods = pjrpc.server.MethodRegistry()
    validator = validators.PydanticValidator()

    auth = flask_httpauth.HTTPBasicAuth()
    credentials = {"admin": security.generate_password_hash("admin")}


    @auth.verify_password
    def verify_password(username: str, password: str) -> Optional[str]:
        if username in credentials and security.check_password_hash(credentials.get(username), password):
            return username


    class AuthenticatedJsonRPC(integration.JsonRPC):
        @auth.login_required
        def _rpc_handle(self, dispatcher: pjrpc.server.Dispatcher) -> flask.Response:
            return super()._rpc_handle(dispatcher)


    class JSONEncoder(pjrpc.JSONEncoder):
        def default(self, o: Any) -> Any:
            if isinstance(o, pd.BaseModel):
                return o.model_dump()
            if isinstance(o, uuid.UUID):
                return str(o)

            return super().default(o)


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
        pd.Field(description="User age", examples=[25]),
    ]

    UserId = Annotated[
        uuid.UUID,
        pd.Field(description="User identifier", examples=["c47726c6-a232-45f1-944f-60b98966ff1b"]),
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


    class AlreadyExistsError(pjrpc.exc.JsonRpcError):
        """
        User already registered error.
        """

        code = 2001
        message = "user already exists"


    class NotFoundError(pjrpc.exc.JsonRpcError):
        """
        User not found error.
        """

        code = 2002
        message = "user not found"


    @specs.annotate(
        summary='Creates a user',
        tags=['users'],
        errors=[AlreadyExistsError],
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

        return UserOut(id=user_id, **user.model_dump())


    @specs.annotate(
        summary='Returns a user',
        tags=['users'],
        errors=[NotFoundError],
    )
    @methods.add
    @validator.validate
    def get_user(user_id: UserId) -> UserOut:
        """
        Returns a user.

        :param object user_id: user id
        :return object: registered user
        :raise NotFoundError: user not found
        """

        user = flask.current_app.users_db.get(user_id.hex)
        if not user:
            raise NotFoundError()

        return UserOut(id=user_id, **user.model_dump())


    @specs.annotate(
        summary='Deletes a user',
        tags=['users'],
        errors=[NotFoundError],
    )
    @methods.add
    @validator.validate
    def delete_user(user_id: UserId) -> None:
        """
        Deletes a user.

        :param object user_id: user id
        :raise NotFoundError: user not found
        """

        user = flask.current_app.users_db.pop(user_id.hex, None)
        if not user:
            raise NotFoundError()


    json_rpc = AuthenticatedJsonRPC(
        '/api/v1',
        json_encoder=JSONEncoder,
        spec=specs.OpenAPI(
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
            schema_extractor=extractors.pydantic.PydanticSchemaExtractor(),
            ui=specs.SwaggerUI(),
        ),
    )
    json_rpc.dispatcher.add_methods(methods)

    app.users_db = {}

    myapp = flask.Blueprint('myapp', __name__, url_prefix='/myapp')
    json_rpc.init_app(myapp)

    app.register_blueprint(myapp)

    if __name__ == "__main__":
        app.run(port=8080)


Specification is available on http://localhost:8080/myapp/api/v1/openapi.json

Web UI is running on http://localhost:8080/myapp/api/v1/ui/

Swagger UI:
~~~~~~~~~~~

.. image:: ../_static/swagger-ui-screenshot.png
  :width: 1024
  :alt: OpenAPI full example

RapiDoc:
~~~~~~~~

.. image:: ../_static/rapidoc-screenshot.png
  :width: 1024
  :alt: OpenAPI cli example

ReDoc:
~~~~~~

.. image:: ../_static/redoc-screenshot.png
  :width: 1024
  :alt: OpenAPI method example
