import uuid
from typing import Any

from litestar import Litestar, Request
import pydantic

import pjrpc.server.specs.extractors.docstring
import pjrpc.server.specs.extractors.pydantic
from pjrpc.server.integration import litestar as integration
from pjrpc.server.specs import extractors
from pjrpc.server.specs import openapi as specs
from pjrpc.server.validators import pydantic as validators

methods = pjrpc.server.MethodRegistry()
validator = validators.PydanticValidator()

credentials = {"admin": "admin"}


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
# @methods.add(context='request')
@validator.validate
def add_user(request: Request, user: UserIn) -> UserOut:
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
# @methods.add(context='request')
@validator.validate
def get_user(request: Request, user_id: uuid.UUID) -> UserOut:
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
# @methods.add(context='request')
@validator.validate
def delete_user(request: Request, user_id: uuid.UUID) -> None:
    """
    Deletes a user.

    :param request: http request
    :param object user_id: user id
    :raise NotFoundError: user not found
    """

    user = request.config_dict['users'].pop(user_id.hex, None)
    if not user:
        raise NotFoundError()


app = Litestar()
app.state['users'] = {}

jsonrpc_app = integration.Application(
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
        schema_extractors=[
            extractors.docstring.DocstringSchemaExtractor(),
            extractors.pydantic.PydanticSchemaExtractor(),
        ],
        ui=specs.SwaggerUI(),
        # ui=specs.RapiDoc(),
        # ui=specs.ReDoc(),
    ),
)
jsonrpc_app.dispatcher.add_methods(methods)
app.register(jsonrpc_app.router)

# cors = aiohttp_cors.setup(
#     app, defaults={
#         '*': aiohttp_cors.ResourceOptions(
#             allow_credentials=True,
#             expose_headers='*',
#             allow_headers='*',
#         ),
#     },
# )
# for route in list(app.router.routes()):
#     cors.add(route)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(jsonrpc_app.app, host='localhost', port=8080)
