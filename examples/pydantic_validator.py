import enum
import uuid
from typing import List

import pydantic
from aiohttp import web

import pjrpc.server
from pjrpc.server.integration import aiohttp
from pjrpc.server.validators import pydantic as validators

methods = pjrpc.server.MethodRegistry()
validator = validators.PydanticValidator()


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
    contacts: List[Contact]


@methods.add(context='request')
@validator.validate
async def add_user(request: web.Request, user: User):
    user_id = uuid.uuid4()
    request.app['users'][user_id] = user

    return {'id': user_id, **user.model_dump()}


class JSONEncoder(pjrpc.server.JSONEncoder):

    def default(self, o):
        if isinstance(o, uuid.UUID):
            return o.hex
        if isinstance(o, enum.Enum):
            return o.value

        return super().default(o)


jsonrpc_app = aiohttp.Application('/api/v1', json_encoder=JSONEncoder)
jsonrpc_app.dispatcher.add_methods(methods)
jsonrpc_app.app['users'] = {}

if __name__ == "__main__":
    web.run_app(jsonrpc_app.app, host='localhost', port=8080)
