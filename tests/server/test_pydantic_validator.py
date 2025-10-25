import pytest

from pjrpc.server.utils import exclude_named_param
from pjrpc.server.validators import ValidationError, pydantic


@pytest.mark.parametrize(
    'dyn_method, params', [
        ('param1: int, param2: int', [1, 2]),
        ('param1: int = 1', []),
        ('param1: int, param2: int = 2', [1]),
        ('param1: int, param2: int', {'param1': 1, 'param2': 2}),
        ('param1: int = 1', {}),
        ('param1: int, param2: int = 2', {'param1': 1}),
        ('param1, param2: int', [1, 2]),
        ('param1, param2: int', ['param1', 2]),
    ], indirect=['dyn_method'],
)
def test_validation_success(dyn_method, params):
    validator_factory = pydantic.PydanticValidatorFactory()
    validator = validator_factory.build(dyn_method)

    validator.validate_params(params)
    validator.validate_params(params)


@pytest.mark.parametrize(
    'dyn_method, params', [
        ('param1: int, param2: int', [1]),
        ('param1: int, param2: int', [1, 2, 3]),
        ('param1: int, param2: int', {'param1': 1}),
        ('param1: int, param2: int', {'param1': 1, 'param2': 2, 'param3': 3}),
    ], indirect=['dyn_method'],
)
def test_validation_error(dyn_method, params):
    validator_factory = pydantic.PydanticValidatorFactory()
    validator = validator_factory.build(dyn_method)

    with pytest.raises(ValidationError):
        validator.validate_params(params)


@pytest.mark.parametrize(
    'dyn_method, exclude, params', [
        ('context, param1: int', ('context',), [1]),
        ('context, param1: int', ('context',), {'param1': 1}),
    ], indirect=['dyn_method'],
)
def test_validation_exclude_success(dyn_method, exclude, params):
    validator_factory = pydantic.PydanticValidatorFactory(exclude=exclude_named_param('context'))
    validator = validator_factory.build(dyn_method)

    validator.validate_params(params)


@pytest.mark.parametrize(
    'dyn_method, exclude, params', [
        ('context, param1: int', ('context',), [1, 2]),
        ('context, param1: int', ('context',), {'context': '', 'param1': 1}),
    ], indirect=['dyn_method'],
)
def test_validation_exclude_error(dyn_method, exclude, params):
    validator_factory = pydantic.PydanticValidatorFactory(exclude=exclude_named_param('context'))
    validator = validator_factory.build(dyn_method)

    with pytest.raises(ValidationError):
        validator.validate_params(params)
