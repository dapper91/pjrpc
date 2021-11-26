import uuid
from typing import Any

import flask
import pydantic
from flask_cors import CORS

import pjrpc.server.specs.extractors.pydantic
import pjrpc.server.specs.extractors.docstring
from pjrpc.server.integration import flask as integration
from pjrpc.server.validators import pydantic as validators
from pjrpc.server.specs import extractors, openrpc as specs

app = flask.Flask(__name__)
CORS(app, resources={r"/api/v1/*": {"origins": "*"}})

methods = pjrpc.server.MethodRegistry()
validator = validators.PydanticValidator()


class JsonEncoder(pjrpc.JSONEncoder):
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
    errors=[AlreadyExistsError],
    tags=['users'],
    examples=[
        specs.MethodExample(
            name='Simple user',
            params=[
                specs.ExampleObject(
                    name='user',
                    value={
                        'name': 'John',
                        'surname': 'Doe',
                        'age': 25,
                    },
                ),
            ],
            result=specs.ExampleObject(
                name='result',
                value={
                    'id': 'c47726c6-a232-45f1-944f-60b98966ff1b',
                    'name': 'John',
                    'surname': 'Doe',
                    'age': 25,
                },
            ),
        ),
    ],
)
@methods.add
@validator.validate
def add_user(user: UserIn) -> UserOut:
    """
    Adds a new user.

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
            name='Simple example',
            params=[
                specs.ExampleObject(
                    name='user',
                    value={
                        'user_id': 'c47726c6-a232-45f1-944f-60b98966ff1b',
                    },
                ),
            ],
            result=specs.ExampleObject(
                name="result",
                value={
                    'id': 'c47726c6-a232-45f1-944f-60b98966ff1b',
                    'name': 'John',
                    'surname': 'Doe',
                    'age': 25,
                },
            ),
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
            name='Simple example',
            summary='Simple example',
            params=[
                specs.ExampleObject(
                    name='user',
                    value={
                        'user_id': 'c47726c6-a232-45f1-944f-60b98966ff1b',
                    },
                ),
            ],
            result=specs.ExampleObject(
                name="result",
                value=None,
            ),
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


json_rpc = integration.JsonRPC(
    '/api/v1',
    json_encoder=JsonEncoder,
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
json_rpc.dispatcher.add_methods(methods)

app.users_db = {}

json_rpc.init_app(app)

if __name__ == "__main__":
    app.run(port=8080)
