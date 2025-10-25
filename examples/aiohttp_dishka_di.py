import uuid
from typing import Any, Optional, Type

import pydantic
from aiohttp import web
from dishka import FromDishka, Provider, Scope, make_async_container, provide
from dishka.integrations.aiohttp import inject, setup_dishka

import pjrpc.server
import pjrpc.server.specs.extractors.pydantic
from pjrpc.server.integration import aiohttp
from pjrpc.server.specs import extractors, openapi
from pjrpc.server.validators import pydantic as validators


def is_di_injected(idx: int, name: str, annotation: Type[Any], default: Any) -> bool:
    return annotation is FromDishka


def exclude_param(idx: int, name: str, annotation: Type[Any], default: Any) -> bool:
    return aiohttp.is_aiohttp_request(idx, name, annotation, default) or is_di_injected(idx, name, annotation, default)


methods = pjrpc.server.MethodRegistry(
    validator_factory=validators.PydanticValidatorFactory(exclude=exclude_param),
    metadata_processors=[
        openapi.MethodSpecificationGenerator(
            extractors.pydantic.PydanticMethodInfoExtractor(exclude=exclude_param),
        ),
    ],
)


class UserService:
    def __init__(self):
        self._users = {}

    def add_user(self, user: dict) -> str:
        user_id = uuid.uuid4().hex
        self._users[user_id] = user

        return user_id

    def get_user(self, user_id: uuid.UUID) -> Optional[dict]:
        return self._users.get(user_id)


class User(pydantic.BaseModel):
    name: str
    surname: str
    age: int


@methods.add(
    pass_context=True,
    metadata=[
        openapi.metadata(
            summary='Creates a user',
            tags=['users'],
        ),
    ],
)
@inject
async def add_user(
    request: web.Request,
    user_service: FromDishka[UserService],
    user: User,
) -> dict:
    user_dict = user.model_dump()
    user_id = user_service.add_user(user_dict)

    return {'id': user_id, **user_dict}


openapi_spec = openapi.OpenAPI(info=openapi.Info(version="1.0.0", title="User storage"))

jsonrpc_app = aiohttp.Application('/api/v1')
jsonrpc_app.add_methods(methods)
jsonrpc_app.add_spec(openapi_spec, path='openapi.json')

jsonrpc_app.http_app['users'] = {}


class ServiceProvider(Provider):
    user_service = provide(UserService, scope=Scope.APP)


setup_dishka(
    app=jsonrpc_app.http_app,
    container=make_async_container(
        ServiceProvider(),
    ),
)

if __name__ == "__main__":
    web.run_app(jsonrpc_app.http_app, host='localhost', port=8080)
