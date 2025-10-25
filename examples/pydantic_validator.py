import enum
import uuid

import pydantic
from aiohttp import web

import pjrpc.server
from pjrpc.server.integration import aiohttp
from pjrpc.server.validators import pydantic as validators

methods = pjrpc.server.MethodRegistry(
    validator_factory=validators.PydanticValidatorFactory(exclude=aiohttp.is_aiohttp_request),
)


class ContactType(enum.Enum):
    PHONE = 'phone'
    EMAIL = 'email'


class Contact(pydantic.BaseModel):
    type: ContactType
    value: str


class User(pydantic.BaseModel):
    name: str
    surname: str
    age: int
    contacts: list[Contact]


class UserOut(User):
    id: uuid.UUID


@methods.add(pass_context='request')
async def add_user(request: web.Request, user: User) -> UserOut:
    user_id = uuid.uuid4()
    request.app['users'][user_id] = user

    return UserOut(id=user_id, **user.model_dump())


class JSONEncoder(pjrpc.server.JSONEncoder):
    def default(self, o):
        if isinstance(o, uuid.UUID):
            return o.hex
        if isinstance(o, enum.Enum):
            return o.value
        if isinstance(o, pydantic.BaseModel):
            return o.model_dump()

        return super().default(o)


jsonrpc_app = aiohttp.Application('/api/v1', json_encoder=JSONEncoder)
jsonrpc_app.add_methods(methods)
jsonrpc_app.http_app['users'] = {}

if __name__ == "__main__":
    web.run_app(jsonrpc_app.http_app, host='localhost', port=8080)
