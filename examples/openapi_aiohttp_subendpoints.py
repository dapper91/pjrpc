import uuid
from typing import Any

import aiohttp_cors
import pydantic
from aiohttp import web

import pjrpc.server.specs.extractors.docstring
import pjrpc.server.specs.extractors.pydantic
from pjrpc.server.integration import aiohttp as integration
from pjrpc.server.specs import extractors
from pjrpc.server.specs import openapi as specs
from pjrpc.server.validators import pydantic as validators

user_methods = pjrpc.server.MethodRegistry()
post_methods = pjrpc.server.MethodRegistry()
validator = validators.PydanticValidator()


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
@user_methods.add(context='request')
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

    return UserOut(id=user_id, **user.dict())


class PostIn(pydantic.BaseModel):
    """
    User registration data.
    """

    title: str
    content: str


class PostOut(PostIn):
    """
    Registered user data.
    """

    id: uuid.UUID


@specs.annotate(
    tags=['posts'],
    errors=[AlreadyExistsError],
    examples=[
        specs.MethodExample(
            summary="Simple example",
            params=dict(
                post={
                    'title': 'Super post',
                    'content': 'My first post',
                },
            ),
            result={
                'id': 'c47726c6-a232-45f1-944f-60b98966ff1b',
                'title': 'Super post',
                'content': 'My first post',
            },
        ),
    ],
)
@post_methods.add(context='request')
@validator.validate
def add_post(request: web.Request, post: PostIn) -> PostOut:
    """
    Creates a post.

    :param request: http request
    :param object post: post data
    :return object: created post
    """

    post_id = uuid.uuid4().hex
    request.config_dict['posts'][post_id] = post

    return PostOut(id=post_id, **post.dict())


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

jsonrpc_app.app['users'] = {}
jsonrpc_app.app['posts'] = {}

jsonrpc_app.add_endpoint('/users', json_encoder=JSONEncoder).add_methods(user_methods)
jsonrpc_app.add_endpoint('/posts', json_encoder=JSONEncoder).add_methods(post_methods)


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
