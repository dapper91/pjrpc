import uuid
from typing import Annotated, Any

import flask
import pydantic as pd

import pjrpc.server.specs.extractors.pydantic
from pjrpc.server.integration import flask as integration
from pjrpc.server.specs import extractors
from pjrpc.server.specs import openapi as specs
from pjrpc.server.validators import pydantic as validators

app = flask.Flask('myapp')

user_methods_v1 = pjrpc.server.MethodRegistry()
user_methods_v2 = pjrpc.server.MethodRegistry()
validator = validators.PydanticValidator()


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


class AlreadyExistsError(pjrpc.exc.JsonRpcError):
    """
    User already registered error.
    """

    code = 2001
    message = "user already exists"


@specs.annotate(
    tags=['v1', 'users'],
    errors=[AlreadyExistsError],
)
@user_methods_v1.add
@validator.validate
def add_user(user: UserIn) -> UserOut:
    """
    Creates a user.

    :param object user: user data
    :return object: registered user
    :raise AlreadyExistsError: user already exists
    """

    user_id = uuid.uuid4().hex
    flask.current_app.db['users'][user_id] = user

    return UserOut(id=user_id, **user.model_dump())


UserAddress = Annotated[
    str,
    pd.Field(description="User address", examples=["Brownsville, Texas, United States"]),
]


class UserInV2(pd.BaseModel):
    """
    User registration data.
    """

    name: UserName
    surname: UserSurname
    age: UserAge
    address: UserAddress


class UserOutV2(UserInV2):
    """
    Registered user data.
    """

    id: UserId


@specs.annotate(
    tags=['v2', 'users'],
    errors=[AlreadyExistsError],
)
@user_methods_v2.add(name='add_user')
@validator.validate
def add_user_v2(user: UserInV2) -> UserOutV2:
    """
    Creates a user.

    :param object user: user data
    :return object: registered user
    :raise AlreadyExistsError: user already exists
    """

    user_id = uuid.uuid4().hex
    flask.current_app.db['users'][user_id] = user

    return UserOutV2(id=user_id, **user.model_dump())


json_rpc = integration.JsonRPC(
    '/api',
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
app.db = {'users': {}}

json_rpc.add_endpoint('/v1', json_encoder=JSONEncoder).add_methods(user_methods_v1)
json_rpc.add_endpoint('/v2', json_encoder=JSONEncoder).add_methods(user_methods_v2)
json_rpc.init_app(app)

if __name__ == "__main__":
    app.run(port=8080)
