import copy
from typing import Any, Dict, Iterable, List, Type

from pjrpc.common.exceptions import JsonRpcError

REQUEST_SCHEMA: Dict[str, Any] = {
    'title': 'Request',
    'type': 'object',
    'properties': {
        'jsonrpc': {
            'title': 'Version',
            'description': 'JSON-RPC protocol version',
            'type': 'string',
            'enum': ['2.0', '1.0'],
        },
        'id': {
            'title': 'Id',
            'description': 'Request identifier',
            'anyOf': [
                {'type': 'string'},
                {'type': 'integer'},
                {'type': 'null'},
            ],
            'examples': [1],
            'default': None,
        },
        'method': {
            'title': 'Method',
            'description': 'Method name',
            'type': 'string',
        },
        'params': {
            'title': 'Parameters',
            'description': 'Method parameters',
            'type': 'object',
            'properties': {},
        },
    },
    'required': ['jsonrpc', 'method', 'params'],
    'additionalProperties': False,
}

RESULT_SCHEMA: Dict[str, Any] = {
    'title': 'Success',
    'type': 'object',
    'properties': {
        'jsonrpc': {
            'title': 'Version',
            'description': 'JSON-RPC protocol version',
            'type': 'string',
            'enum': ['2.0', '1.0'],
        },
        'id': {
            'title': 'Id',
            'description': 'Request identifier',
            'anyOf': [
                {'type': 'string'},
                {'type': 'integer'},
            ],
            'examples': [1],
        },
        'result': {},
    },
    'required': ['jsonrpc', 'id', 'result'],
    'additionalProperties': False,
}
ERROR_SCHEMA: Dict[str, Any] = {
    'title': 'Error',
    'type': 'object',
    'properties': {
        'jsonrpc': {
            'title': 'Version',
            'description': 'JSON-RPC protocol version',
            'type': 'string',
            'enum': ['2.0', '1.0'],
        },
        'id': {
            'title': 'Id',
            'description': 'Request identifier',
            'anyOf': [
                {'type': 'string'},
                {'type': 'integer'},
            ],
            'examples': [1],
        },
        'error': {
            'type': 'object',
            'properties': {
                'code': {
                    'title': 'Code',
                    'description': 'Error code',
                    'type': 'integer',
                },
                'message': {
                    'title': 'Message',
                    'description': 'Error message',
                    'type': 'string',
                },
                'data': {
                    'title': 'Data',
                    'description': 'Error additional data',
                    'type': 'object',
                },
            },
            'required': ['code', 'message'],
            'additionalProperties': False,
        },
    },
    'required': ['jsonrpc', 'error'],
    'additionalProperties': False,
}


def build_request_schema(method_name: str, parameters_schema: Dict[str, Any]) -> Dict[str, Any]:
    reqeust_schema = copy.deepcopy(REQUEST_SCHEMA)

    reqeust_schema['properties']['method']['const'] = method_name
    reqeust_schema['properties']['params'] = {
        'title': 'Parameters',
        'description': 'Reqeust parameters',
        'type': 'object',
        'properties': parameters_schema,
        'additionalProperties': False,
    }

    return reqeust_schema


def build_response_schema(result_schema: Dict[str, Any], errors: Iterable[Type[JsonRpcError]]) -> Dict[str, Any]:
    response_schema = copy.deepcopy(RESULT_SCHEMA)
    response_schema['properties']['result'] = result_schema

    if errors:
        error_schemas: List[Dict[str, Any]] = []
        for error in errors:
            error_schema = copy.deepcopy(ERROR_SCHEMA)
            error_props = error_schema['properties']['error']['properties']
            error_props['code']['const'] = error.code
            error_props['message']['const'] = error.message
            error_schemas.append(error_schema)

        response_schema = {'oneOf': [response_schema] + error_schemas}

    return response_schema
