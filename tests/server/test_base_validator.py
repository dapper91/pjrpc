import pytest
from pjrpc.server import validators


@pytest.mark.parametrize(
    'dyn_method, params', [
        ('param1, param2', [1, 2]),
        ('param1, *args', [1, 2, 3]),
        ('param1, *args', [1]),
        ('param1=1', []),
        ('param1, param2=2', [1]),
        ('param1, param2', {'param1': 1, 'param2': 2}),
        ('param1, **kwargs', {'param1': 1, 'param2': 2, 'param3': 3}),
        ('param1, *, param2, param3', {'param1': 1, 'param2': 2, 'param3': 3}),
        ('param1=1', {}),
        ('param1, param2=2', {'param1': 1}),
        ('param1, *, param2=2', {'param1': 1}),
    ], indirect=['dyn_method'],
)
def test_validation_success(dyn_method, params):
    validator = validators.BaseValidator()
    validator.validate_method(dyn_method, params)


@pytest.mark.parametrize(
    'dyn_method, params', [
        ('param1, param2', [1]),
        ('param1, param2', [1, 2, 3]),
        ('param1, *args', []),
        ('param1, param2', {'param1': 1}),
        ('param1, param2', {'param1': 1, 'param2': 2, 'param3': 3}),
        ('param1, **kwargs', {'param2': 2}),
        ('param1, *, param2, param3', {'param2': 1}),
    ], indirect=['dyn_method'],
)
def test_validation_error(dyn_method, params):
    validator = validators.BaseValidator()

    with pytest.raises(validators.ValidationError):
        validator.validate_method(dyn_method, params)


@pytest.mark.parametrize(
    'dyn_method, exclude, params', [
        ('context, param1', ('context',), [1]),
        ('context, *args', ('context',), []),
        ('context, param1', ('context',), {'param1': 1}),
        ('context, **kwargs', ('context',), {}),
        ('context, *, param1', ('context',), {'param1': 1}),
    ], indirect=['dyn_method'],
)
def test_validation_exclude_success(dyn_method, exclude, params):
    validator = validators.BaseValidator()
    validator.validate_method(dyn_method, params, exclude=exclude)


@pytest.mark.parametrize(
    'dyn_method, exclude, params', [
        ('context, param1', ('context',), [1, 2]),
        ('context, param1', ('context',), {'context': '', 'param1': 1}),
        ('context, *, param1', ('context',), {'context': 1}),
    ], indirect=['dyn_method'],
)
def test_validation_exclude_error(dyn_method, exclude, params):
    validator = validators.BaseValidator()

    with pytest.raises(validators.ValidationError):
        validator.validate_method(dyn_method, params, exclude=exclude)
