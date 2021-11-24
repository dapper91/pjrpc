import uuid
from typing import Any, Optional

import flask
import flask_httpauth
import pydantic
import flask_cors
from werkzeug import security

import pjrpc.server.specs.extractors.pydantic
from pjrpc.server.integration import flask as integration
from pjrpc.server.validators import pydantic as validators
from pjrpc.server.specs import extractors, openapi as specs


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
        if isinstance(o, pydantic.BaseModel):
            return o.dict()
        if isinstance(o, uuid.UUID):
            return str(o)

        return super().default(o)


class UserIn(pydantic.BaseModel):
    """
    User registration data.
    """

    name: str
    surname: str
    age: int


class UserOut(UserIn):
    """
    Registered user data.
    """

    id: uuid.UUID


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
    tags=['users'],
    errors=[AlreadyExistsError],
    examples=[
        specs.MethodExample(
            summary="Simple example",
            params=dict(
                user={
                    'name': 'John',
                    'surname': 'Doe',
                    'age': 25,
                },
            ),
            result={
                'id': 'c47726c6-a232-45f1-944f-60b98966ff1b',
                'name': 'John',
                'surname': 'Doe',
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


@specs.annotate(
    tags=['users'],
    errors=[NotFoundError],
    examples=[
        specs.MethodExample(
            summary='Simple example',
            params=dict(
                user_id='c47726c6-a232-45f1-944f-60b98966ff1b',
            ),
            result={
                'id': 'c47726c6-a232-45f1-944f-60b98966ff1b',
                'name': 'John',
                'surname': 'Doe',
                'age': 25,
            },
        ),
    ],
)
@methods.add
@validator.validate
def get_user(user_id: uuid.UUID) -> UserOut:
    """
    Returns a user.

    :param object user_id: user id
    :return object: registered user
    :raise NotFoundError: user not found
    """

    user = flask.current_app.users_db.get(user_id.hex)
    if not user:
        raise NotFoundError()

    return UserOut(id=user_id, **user.dict())


@specs.annotate(
    tags=['users'],
    errors=[NotFoundError],
    examples=[
        specs.MethodExample(
            summary='Simple example',
            params=dict(
                user_id='c47726c6-a232-45f1-944f-60b98966ff1b',
            ),
            result=None,
        ),
    ],
)
@methods.add
@validator.validate
def delete_user(user_id: uuid.UUID) -> None:
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
        # ui=specs.RapiDoc(),
        # ui=specs.ReDoc(),
    ),
)
json_rpc.dispatcher.add_methods(methods)

app.users_db = {}

myapp = flask.Blueprint('myapp', __name__, url_prefix='/myapp')
json_rpc.init_app(myapp)

app.register_blueprint(myapp)

if __name__ == "__main__":
    app.run(port=8080)
