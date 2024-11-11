import uuid
from typing import Annotated, Any

import aiohttp_cors
import pydantic as pd
from aiohttp import web

import pjrpc.server.specs.extractors.pydantic
from pjrpc.common.exceptions import MethodNotFoundError
from pjrpc.server.integration import aiohttp as integration
from pjrpc.server.specs import extractors
from pjrpc.server.specs import openapi as specs
from pjrpc.server.validators import pydantic as validators

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


@specs.annotate(
    tags=['v1', 'users'],
    errors=[
        AlreadyExistsError,
    ],
)
@user_methods_v1.add(context='request')
@validator.validate
def add_user(request: web.Request, user: UserIn) -> UserOut:
    """
    Creates a user.

    :param request: http request
    :param object user: user data
    :return object: registered user
    :raise AlreadyExistsError: user already exists
    """

    user_id = uuid.uuid4().hex
    request.config_dict['users'][user_id] = user

    return UserOut(id=user_id, **user.model_dump())


UserAddress = Annotated[
    str,
    pd.Field(description="User address", examples=["Brownsville, Texas, United States"]),
]


class UserInV2(UserIn):
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
    errors=[
        AlreadyExistsError,
    ],
)
@user_methods_v2.add(context='request', name='add_user')
@validator.validate
def add_user_v2(request: web.Request, user: UserInV2) -> UserOutV2:
    """
    Creates a user.

    :param request: http request
    :param object user: user data
    :return object: registered user
    :raise AlreadyExistsError: user already exists
    """

    user_id = uuid.uuid4().hex
    request.config_dict['users'][user_id] = user

    return UserOutV2(id=user_id, **user.model_dump())


error_http_status_map = {
    AlreadyExistsError.code: 400,
    MethodNotFoundError.code: 404,
}

jsonrpc_app = integration.Application(
    '/api',
    json_encoder=JSONEncoder,
    status_by_error=lambda codes: 200 if len(codes) != 1 else error_http_status_map.get(codes[0], 200),
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
        error_http_status_map=error_http_status_map,
    ),
)

jsonrpc_app.app['users'] = {}
jsonrpc_app.app['posts'] = {}

jsonrpc_app_v1 = integration.Application(
    json_encoder=JSONEncoder,
    status_by_error=lambda codes: 200 if len(codes) != 1 else error_http_status_map.get(codes[0], 200),
)
jsonrpc_app_v1.dispatcher.add_methods(user_methods_v1)

jsonrpc_app_v2 = integration.Application(
    json_encoder=JSONEncoder,
    status_by_error=lambda codes: 200 if len(codes) != 1 else error_http_status_map.get(codes[0], 200),
)
jsonrpc_app_v2.dispatcher.add_methods(user_methods_v2)

jsonrpc_app.add_subapp('/v1', jsonrpc_app_v1)
jsonrpc_app.add_subapp('/v2', jsonrpc_app_v2)


cors = aiohttp_cors.setup(
    jsonrpc_app.app, defaults={
        '*': aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers='*',
            allow_headers='*',
        ),
    },
)
for route in list(jsonrpc_app.app.router.routes()):
    cors.add(route)


if __name__ == "__main__":
    web.run_app(jsonrpc_app.app, host='localhost', port=8080)
