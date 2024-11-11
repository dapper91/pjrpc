import uuid
from typing import Annotated, Any

import flask
import pydantic as pd
from flask_cors import CORS

import pjrpc.server.specs.extractors.pydantic
from pjrpc.server.integration import flask as integration
from pjrpc.server.specs import extractors
from pjrpc.server.specs import openrpc as specs
from pjrpc.server.validators import pydantic as validators

app = flask.Flask(__name__)
CORS(app, resources={r"/api/v1/*": {"origins": "*"}})

methods = pjrpc.server.MethodRegistry()
validator = validators.PydanticValidator()


class JsonEncoder(pjrpc.JSONEncoder):
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
    summary='Adds a new user',
    errors=[AlreadyExistsError],
    tags=['users'],
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
