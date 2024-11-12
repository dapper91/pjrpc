import uuid
from typing import Annotated, Any

import aiohttp_cors
import pydantic as pd
from aiohttp import web

import pjrpc.server.specs.extractors.pydantic
from pjrpc.server.integration import aiohttp as integration
from pjrpc.server.specs import extractors
from pjrpc.server.specs import openrpc as specs
from pjrpc.server.validators import pydantic as validators

methods = pjrpc.server.MethodRegistry()
validator = validators.PydanticValidator()

credentials = {"admin": "admin"}


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
    pd.Field(description="User surname", examples=["Doe"]),
]

UserAge = Annotated[
    int,
    pd.Field(description="User age", examples=[25]),
]

UserId = Annotated[
    uuid.UUID,
    pd.Field(description="User identifier", examples=["08b02cf9-8e07-4d06-b569-2c24309c1dc1"]),
]


class UserIn(pd.BaseModel, title="User data"):
    """
    User registration data.
    """

    name: UserName
    surname: UserSurname
    age: UserAge


class UserOut(UserIn, title="User data"):
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
    summary="Creates a user",
    tags=['users'],
    errors=[AlreadyExistsError],
)
@methods.add(context='request')
@validator.validate
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

    user_id = uuid.uuid4().hex
    request.config_dict['users'][user_id] = user

    return UserOut(id=user_id, **user.model_dump())


@specs.annotate(
    summary="Returns a user",
    tags=['users'],
    errors=[NotFoundError],
)
@methods.add(context='request')
@validator.validate
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


@specs.annotate(
    summary="Deletes a user",
    tags=['users'],
    errors=[NotFoundError],
    deprecated=True,
)
@methods.add(context='request')
@validator.validate
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


app = web.Application()
app['users'] = {}

jsonrpc_app = integration.Application(
    '/api/v1',
    json_encoder=JSONEncoder,
    spec=specs.OpenRPC(
        info=specs.Info(version="1.0.0", title="User storage"),
        servers=[
            specs.Server(
                name="api",
                url="http://127.0.0.1:8080/myapp/api",
            ),
        ],
        schema_extractor=extractors.pydantic.PydanticSchemaExtractor(),
    ),
)
jsonrpc_app.dispatcher.add_methods(methods)
app.add_subapp('/myapp', jsonrpc_app.app)

cors = aiohttp_cors.setup(
    app, defaults={
        '*': aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers='*',
            allow_headers='*',
        ),
    },
)
for route in list(app.router.routes()):
    cors.add(route)

if __name__ == "__main__":
    web.run_app(app, host='localhost', port=8080)
