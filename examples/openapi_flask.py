import uuid
from typing import Annotated, Any

import flask
import flask_cors
import pydantic as pd

import pjrpc.server.specs.extractors.pydantic
import pjrpc.server.specs.openapi.ui
from pjrpc.server.integration import flask as integration
from pjrpc.server.specs import extractors, openapi
from pjrpc.server.validators import pydantic as validators

methods = pjrpc.server.MethodRegistry(
    validator_factory=validators.PydanticValidatorFactory(),
    metadata_processors=[
        openapi.MethodSpecificationGenerator(
            extractor=extractors.pydantic.PydanticMethodInfoExtractor(),
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
    metadata=[
        openapi.metadata(
            summary='Creates a user',
            tags=['users'],
            errors=[AlreadyExistsError],
        ),
    ],
)
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

    user_id = uuid.uuid4()
    flask.current_app.users_db[user_id] = user

    return UserOut(id=user_id, **user.model_dump())


@methods.add(
    metadata=[
        openapi.metadata(
            summary='Returns a user',
            tags=['users'],
            errors=[NotFoundError],
        ),
    ],
)
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


@methods.add(
    metadata=[
        openapi.metadata(
            summary='Deletes a user',
            tags=['users'],
            errors=[NotFoundError],
        ),
    ],
)
def delete_user(user_id: UserId) -> None:
    """
    Deletes a user.

    :param object user_id: user id
    :raise NotFoundError: user not found
    """

    user = flask.current_app.users_db.pop(user_id.hex, None)
    if not user:
        raise NotFoundError()


class JSONEncoder(pjrpc.server.JSONEncoder):
    def default(self, o: Any) -> Any:
        if isinstance(o, pd.BaseModel):
            return o.model_dump()
        if isinstance(o, uuid.UUID):
            return str(o)

        return super().default(o)


openapi_spec = openapi.OpenAPI(
    info=openapi.Info(version="1.0.0", title="User storage"),
    servers=[
        openapi.Server(
            url='http://127.0.0.1:8080',
        ),
    ],
    security_schemes=dict(
        basicAuth=openapi.SecurityScheme(
            type=openapi.SecuritySchemeType.HTTP,
            scheme='basic',
        ),
    ),
    security=[
        dict(basicAuth=[]),
    ],
)


jsonrpc_v1 = integration.JsonRPC('/api/v1', json_encoder=JSONEncoder)
jsonrpc_v1.add_methods(methods)
jsonrpc_v1.add_spec(openapi_spec, path='openapi.json')
jsonrpc_v1.add_spec_ui('swagger', ui=openapi.ui.SwaggerUI(), spec_url='../openapi.json')

flask_cors.CORS(jsonrpc_v1.http_app, resources={"/rpc/api/v1/*": {"origins": "*"}})
jsonrpc_v1.http_app.users_db = {}


if __name__ == "__main__":
    jsonrpc_v1.http_app.run(port=8080)
