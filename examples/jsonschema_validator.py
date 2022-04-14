import uuid

from aiohttp import web

import xjsonrpc.server
from xjsonrpc.server.validators import jsonschema as validators
from xjsonrpc.server.integration import aiohttp

methods = xjsonrpc.server.MethodRegistry()
validator = validators.JsonSchemaValidator()


contact_schema = {
    'type': 'object',
    'properties': {
        'type': {
            'type': 'string',
            'enum': ['phone', 'email'],
        },
        'value': {'type': 'string'},
    },
    'required': ['type', 'value'],
}

user_schema = {
    'type': 'object',
    'properties': {
        'name': {'type': 'string'},
        'surname': {'type': 'string'},
        'age': {'type': 'integer'},
        'contacts': {
            'type': 'array',
            'items': contact_schema,
        },
    },
    'required': ['name', 'surname', 'age', 'contacts'],
}

params_schema = {
    'type': 'object',
    'properties': {
        'user': user_schema,
    },
    'required': ['user'],
}


@methods.add(context='request')
@validator.validate(schema=params_schema)
async def add_user(request: web.Request, user):
    user_id = uuid.uuid4().hex
    request.app['users'][user_id] = user

    return {'id': user_id, **user}


jsonrpc_app = aiohttp.Application('/api/v1')
jsonrpc_app.dispatcher.add_methods(methods)
jsonrpc_app.app['users'] = {}

if __name__ == "__main__":
    web.run_app(jsonrpc_app.app, host='localhost', port=8080)
