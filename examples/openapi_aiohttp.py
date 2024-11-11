import uuid
from typing import Annotated, Any

import aiohttp_cors
import pydantic as pd
from aiohttp import helpers, web

import pjrpc.server.specs.extractors.pydantic
from pjrpc.server.integration import aiohttp as integration
from pjrpc.server.specs import extractors
from pjrpc.server.specs import openapi as specs
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


class AuthenticatedJsonRPC(integration.Application):
    async def _rpc_handle(self, http_request: web.Request, dispatcher: pjrpc.server.Dispatcher) -> web.Response:
        try:
            auth = helpers.BasicAuth.decode(http_request.headers.get('Authorization', ''))
        except ValueError:
            raise web.HTTPUnauthorized

        if credentials.get(auth.login) != auth.password:
            raise web.HTTPUnauthorized

        return await super()._rpc_handle(http_request=http_request, dispatcher=dispatcher)


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
    summary='Returns a user',
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
    summary='Deletes a user',
    tags=['users'],
    errors=[NotFoundError],
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

jsonrpc_app = AuthenticatedJsonRPC(
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
