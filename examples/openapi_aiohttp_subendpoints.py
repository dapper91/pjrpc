import uuid
from typing import Annotated, Any

import aiohttp_cors
import pydantic as pd
from aiohttp import web

import pjrpc.server.specs.extractors.docstring
import pjrpc.server.specs.extractors.pydantic
from pjrpc.common.exceptions import MethodNotFoundError
from pjrpc.server.integration import aiohttp as integration
from pjrpc.server.specs import extractors
from pjrpc.server.specs import openapi as specs
from pjrpc.server.validators import pydantic as validators

user_methods = pjrpc.server.MethodRegistry()
post_methods = pjrpc.server.MethodRegistry()
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
    # tags=['users'],
    errors=[AlreadyExistsError],
    # examples=[
    #     specs.MethodExample(
    #         summary="Simple example",
    #         params=dict(
    #             user={
    #                 'name': 'John',
    #                 'surname': 'Doe',
    #                 'age': 25,
    #             },
    #         ),
    #         result={
    #             'id': 'c47726c6-a232-45f1-944f-60b98966ff1b',
    #             'name': 'John',
    #             'surname': 'Doe',
    #             'age': 25,
    #         },
    #     ),
    # ],
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

    return UserOut(id=user_id, **user.model_dump())


PostTitle = Annotated[
    str,
    pd.Field(description="Post title", examples=["About me"]),
]

PostContent = Annotated[
    str,
    pd.Field(description="Post content", examples=['Software engineer']),
]

PostId = Annotated[
    uuid.UUID,
    pd.Field(description="Post identifier", examples=["226a2c23-c98b-4729-b398-0dae550e99ff"]),
]


class PostIn(pd.BaseModel):
    """
    User registration data.
    """

    title: PostTitle
    content: PostContent


class PostOut(PostIn):
    """
    Registered user data.
    """

    id: PostId


@specs.annotate(
    # tags=['posts'],
    errors=[AlreadyExistsError],
    # examples=[
    #     specs.MethodExample(
    #         summary="Simple example",
    #         params=dict(
    #             post={
    #                 'title': 'Super post',
    #                 'content': 'My first post',
    #             },
    #         ),
    #         result={
    #             'id': 'c47726c6-a232-45f1-944f-60b98966ff1b',
    #             'title': 'Super post',
    #             'content': 'My first post',
    #         },
    #     ),
    # ],
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


error_http_status_map = {
    AlreadyExistsError.code: 400,
    MethodNotFoundError.code: 404,
}

jsonrpc_app = integration.Application(
    '/api/v1',
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
        schema_extractors=[
            extractors.pydantic.PydanticSchemaExtractor(),
        ],
        # ui=specs.SwaggerUI(),
        # ui=specs.RapiDoc(),
        ui=specs.ReDoc(hide_schema_titles=True),
        error_http_status_map=error_http_status_map,
    ),
)

jsonrpc_app.app['users'] = {}
jsonrpc_app.app['posts'] = {}

jsonrpc_app.add_endpoint(
    '/users',
    json_encoder=JSONEncoder,
    spec_params=dict(
        method_schema_extra={'tags': ['users']},
        component_name_prefix='V1',
    ),
).add_methods(user_methods)
jsonrpc_app.add_endpoint(
    '/posts',
    json_encoder=JSONEncoder,
    spec_params=dict(
        method_schema_extra={'tags': ['posts']},
        component_name_prefix='V1',
    ),
).add_methods(post_methods)


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
