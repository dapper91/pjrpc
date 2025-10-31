import uuid
from typing import Annotated, Any

import aiohttp_cors
import pydantic as pd
from aiohttp import web

import pjrpc.server.specs.extractors.pydantic
import pjrpc.server.specs.openapi.ui
from pjrpc.server.exceptions import MethodNotFoundError
from pjrpc.server.integration import aiohttp as integration
from pjrpc.server.specs import extractors, openapi, openrpc
from pjrpc.server.validators import pydantic as validators


class AlreadyExistsError(pjrpc.server.exceptions.TypedError):
    """
    User already registered error.
    """

    CODE = 2001
    MESSAGE = "user already exists"


error_http_status_map = {
    AlreadyExistsError.CODE: 400,
    MethodNotFoundError.CODE: 404,
}


def http_status_by_jsonrpc_codes(codes: tuple[int, ...]) -> int:
    if len(codes) != 1:
        return 200
    else:
        return error_http_status_map.get(codes[0], 200)


method_validator_factory = validators.PydanticValidatorFactory(exclude=integration.is_aiohttp_request)
method_info_extractor = extractors.pydantic.PydanticMethodInfoExtractor(exclude=integration.is_aiohttp_request)
openrpc_method_spec_generator = openrpc.MethodSpecificationGenerator(method_info_extractor)
openapi_method_spec_generator = openapi.MethodSpecificationGenerator(method_info_extractor, error_http_status_map)

methods_v1 = pjrpc.server.MethodRegistry(
    validator_factory=method_validator_factory,
    metadata=[
        openapi.metadata(tags=['v1']),
    ],
    metadata_processors=[
        openrpc_method_spec_generator,
        openapi_method_spec_generator,
    ],
)
methods_v2 = pjrpc.server.MethodRegistry(
    validator_factory=method_validator_factory,
    metadata=[
        openapi.metadata(tags=['v2']),
    ],
    metadata_processors=[
        openrpc_method_spec_generator,
        openapi_method_spec_generator,
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


@methods_v1.add(
    pass_context=True,
    metadata=[
        openapi.metadata(
            tags=['users'],
            errors=[AlreadyExistsError],
        ),
        openrpc.metadata(
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

    user_id = uuid.uuid4()
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


@methods_v2.add(
    pass_context=True,
    name='add_user',
    metadata=[
        openapi.metadata(
            tags=['users'],
            errors=[AlreadyExistsError],
        ),
        openrpc.metadata(
            tags=['users'],
            errors=[AlreadyExistsError],
        ),
    ],
)
def add_user2(request: web.Request, user: UserInV2) -> UserOutV2:
    """
    Creates a user.

    :param request: http request
    :param object user: user data
    :return object: registered user
    :raise AlreadyExistsError: user already exists
    """

    user_id = uuid.uuid4()
    request.config_dict['users'][user_id] = user

    return UserOutV2(id=user_id, **user.model_dump())


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

openrpc_spec = openrpc.OpenRPC(
    info=openrpc.Info(version="1.0.0", title="User storage"),
    servers=[
        openapi.Server(
            url='http://127.0.0.1:8080',
        ),
    ],
)


class JSONEncoder(pjrpc.server.JSONEncoder):
    def default(self, o: Any) -> Any:
        if isinstance(o, pd.BaseModel):
            return o.model_dump()
        if isinstance(o, uuid.UUID):
            return str(o)

        return super().default(o)


jsonrpc_app = integration.Application(
    '/api',
    json_encoder=JSONEncoder,
    status_by_error=http_status_by_jsonrpc_codes,
)
jsonrpc_app.add_spec(spec=openapi_spec, path='openapi.json')
jsonrpc_app.add_spec_ui('/swagger', openapi.ui.SwaggerUI(), spec_url='../openapi.json')
jsonrpc_app.add_spec_ui('/redoc', openapi.ui.ReDoc(hide_schema_titles=True), spec_url='../openapi.json')
jsonrpc_app.http_app['users'] = {}

jsonrpc_app_v1 = integration.Application(
    json_encoder=JSONEncoder,
    status_by_error=http_status_by_jsonrpc_codes,
)
jsonrpc_app_v1.add_methods(methods_v1)
jsonrpc_app_v1.add_spec(spec=openrpc_spec, path='openrpc.json')

jsonrpc_app_v2 = integration.Application(json_encoder=JSONEncoder, status_by_error=http_status_by_jsonrpc_codes)
jsonrpc_app_v2.add_methods(methods_v2)
jsonrpc_app_v2.add_spec(spec=openrpc_spec, path='openrpc.json')

jsonrpc_app.add_subapp('/v1', jsonrpc_app_v1)
jsonrpc_app.add_subapp('/v2', jsonrpc_app_v2)

cors = aiohttp_cors.setup(
    jsonrpc_app.http_app, defaults={
        '*': aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers='*',
            allow_headers='*',
        ),
    },
)
for route in list(jsonrpc_app.http_app.router.routes()):
    cors.add(route)


if __name__ == "__main__":
    web.run_app(jsonrpc_app.http_app, host='localhost', port=8080)
