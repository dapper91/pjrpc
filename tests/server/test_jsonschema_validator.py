import pytest
from pjrpc.server import validators
from pjrpc.server.validators import jsonschema


@pytest.mark.parametrize(
    'dyn_method, params, schema', [
        (
            'param1, param2',
            [1, 2],
            {
                'type': 'object',
                'properties': {
                    'param1': {'type': 'integer'},
                    'param2': {'type': 'integer'},
                },
            },
        ),
        (
            'param1, *args',
            [1, 2, 3],
            {
                'type': 'object',
                'properties': {
                    'param1': {'type': 'integer'},
                    'args': {
                        'type': 'array',
                        'items': {
                            'type': 'integer',
                        },
                    },
                },
            },
        ),
        (
            'param1, *args',
            [1],
            {
                'type': 'object',
                'properties': {
                    'param1': {'type': 'integer'},
                    'args': {
                        'type': 'array',
                        'items': {
                            'type': 'integer',
                        },
                    },
                },
            },
        ),
        (
            'param1=1',
            [],
            {
                'type': 'object',
                'properties': {
                    'param1': {'type': 'integer'},
                },
            },

        ),
        (
            'param1, param2=2',
            [1],
            {
                'type': 'object',
                'properties': {
                    'param1': {'type': 'integer'},
                    'param2': {'type': 'integer'},
                },
            },
        ),
        (
            'param1, param2',
            {
                'param1': 1,
                'param2': 2,
            },
            {
                'type': 'object',
                'properties': {
                    'param1': {'type': 'integer'},
                    'param2': {'type': 'integer'},
                },
            },
        ),
        (
            'param1, **kwargs',
            {
                'param1': 1,
                'param2': 2,
                'param3': 3,
            },
            {
                'type': 'object',
                'properties': {
                    'param1': {'type': 'integer'},
                    'kwargs': {'type': 'object'},
                },
            },
        ),
        (
            'param1, *, param2, param3',
            {
                'param1': 1,
                'param2': 2,
                'param3': 3,
            },
            {
                'type': 'object',
                'properties': {
                    'param1': {'type': 'integer'},
                    'param2': {'type': 'integer'},
                    'param3': {'type': 'integer'},
                },
            },

        ),
        (
            'param1=1',
            {},
            {
                'type': 'object',
                'properties': {
                    'param1': {'type': 'integer'},
                },
            },
        ),
        (
            'param1, param2=2',
            {
                'param1': 1,
            },
            {
                'type': 'object',
                'properties': {
                    'param1': {'type': 'integer'},
                    'param2': {'type': 'integer'},
                },
            },
        ),
        (
            'param1, *, param2=2',
            {
                'param1': 1,
            },
            {
                'type': 'object',
                'properties': {
                    'param1': {'type': 'integer'},
                    'param2': {'type': 'integer'},
                },
            },
        ),
    ], indirect=['dyn_method'],
)
def test_validation_success(dyn_method, params, schema):
    validator = jsonschema.JsonSchemaValidator()
    validator.validate_method(dyn_method, params, schema=schema)


@pytest.mark.parametrize(
    'dyn_method, params, schema', [
        (
            'param1, param2',
            [1],
            {
                'type': 'object',
                'properties': {
                    'param1': {'type': 'integer'},
                    'param2': {'type': 'integer'},
                },
            },
        ),
        (
            'param1, param2',
            [1, 2, 3],
            {
                'type': 'object',
                'properties': {
                    'param1': {'type': 'integer'},
                    'param2': {'type': 'integer'},
                },
            },
        ),
        (
            'param1, *args',
            [],
            {
                'type': 'object',
                'properties': {
                    'param1': {'type': 'integer'},
                    'args': {
                        'type': 'array',
                        'items': {
                            'type': 'integer',
                        },
                    },
                },
            },
        ),
        (
            'param1, param2',
            {
                'param1': 1,
            },
            {
                'type': 'object',
                'properties': {
                    'param1': {'type': 'integer'},
                    'param2': {'type': 'integer'},
                },
            },
        ),
        (
            'param1, param2',
            {
                'param1': 1,
                'param2': 2,
                'param3': 3,
            },
            {
                'type': 'object',
                'properties': {
                    'param1': {'type': 'integer'},
                    'param2': {'type': 'integer'},
                },
            },
        ),
        (
            'param1, **kwargs',
            {
                'param2': 2,
            },
            {
                'type': 'object',
                'properties': {
                    'param1': {'type': 'integer'},
                    'kwargs': {'type': 'object'},
                },
            },
        ),
        (
            'param1, *, param2, param3',
            {
                'param2': 1,
            },
            {
                'type': 'object',
                'properties': {
                    'param1': {'type': 'integer'},
                    'param2': {'type': 'integer'},
                    'param3': {'type': 'integer'},
                },
            },
        ),
    ], indirect=['dyn_method'],
)
def test_validation_error(dyn_method, params, schema):
    validator = jsonschema.JsonSchemaValidator()

    with pytest.raises(validators.ValidationError):
        validator.validate_method(dyn_method, params, schema=schema)
