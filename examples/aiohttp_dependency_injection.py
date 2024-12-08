import uuid
from typing import Any, Optional, Type

import pydantic
from aiohttp import web
from dependency_injector import containers, providers
from dependency_injector.wiring import Provide, inject

import pjrpc.server
import pjrpc.server.specs.extractors.pydantic
from pjrpc.server.integration import aiohttp
from pjrpc.server.specs import extractors
from pjrpc.server.specs import openapi as specs
from pjrpc.server.validators import pydantic as validators


def is_di_injected(name: str, annotation: Type[Any], default: Any) -> bool:
    return type(default) is Provide


methods = pjrpc.server.MethodRegistry()
validator = validators.PydanticValidator(exclude_param=is_di_injected)


class UserService:
    def __init__(self):
        self._users = {}

    def add_user(self, user: dict) -> str:
        user_id = uuid.uuid4().hex
        self._users[user_id] = user

        return user_id

    def get_user(self, user_id: uuid.UUID) -> Optional[dict]:
        return self._users.get(user_id)


class Container(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(modules=["__main__"])
    user_service = providers.Factory(UserService)


class User(pydantic.BaseModel):
    name: str
    surname: str
    age: int


@specs.annotate(summary='Creates a user', tags=['users'])
@methods.add(context='request')
@validator.validate
@inject
async def add_user(
    request: web.Request,
    user: User,
    user_service: UserService = Provide[Container.user_service],
) -> dict:
    user_dict = user.model_dump()
    user_id = user_service.add_user(user_dict)

    return {'id': user_id, **user_dict}


jsonrpc_app = aiohttp.Application(
    '/api/v1',
    specs=[
        specs.OpenAPI(
            info=specs.Info(version="1.0.0", title="User storage"),
            schema_extractor=extractors.pydantic.PydanticSchemaExtractor(exclude_param=is_di_injected),
            ui=specs.SwaggerUI(),
        ),
    ],
)
jsonrpc_app.dispatcher.add_methods(methods)
jsonrpc_app.app['users'] = {}

jsonrpc_app.app.container = Container()

if __name__ == "__main__":
    web.run_app(jsonrpc_app.app, host='localhost', port=8080)
