import pytest

import pjrpc
from pjrpc.client import exceptions


def test_error_serialization():
    error = exceptions.ServerError()

    actual_dict = error.to_json()
    expected_dict = {
        'code': -32000,
        'message': 'Server error',
    }

    assert actual_dict == expected_dict


def test_error_deserialization():
    data = {
        'code': -32000,
        'message': 'Server error',
    }

    error = exceptions.ServerError.from_json(data)

    assert error.code == -32000
    assert error.message == 'Server error'


def test_error_data_serialization():
    error = exceptions.MethodNotFoundError(data='method_name')

    actual_dict = error.to_json()
    expected_dict = {
        'code': -32601,
        'message': 'Method not found',
        'data': 'method_name',
    }

    assert actual_dict == expected_dict


def test_custom_error_data_serialization():
    error = exceptions.JsonRpcError(code=2001, message='Custom error', data='additional data')

    actual_dict = error.to_json()
    expected_dict = {
        'code': 2001,
        'message': 'Custom error',
        'data': 'additional data',
    }

    assert actual_dict == expected_dict


def test_custom_error_data_deserialization():
    data = {
        'code': -32601,
        'message': 'Method not found',
        'data': 'method_name',
    }

    error = exceptions.JsonRpcError.from_json(data)

    assert error.code == -32601
    assert error.message == 'Method not found'
    assert error.data == 'method_name'


def test_error_deserialization_errors():
    with pytest.raises(pjrpc.exc.DeserializationError, match="data must be of type dict"):
        exceptions.JsonRpcError.from_json([])

    with pytest.raises(pjrpc.exc.DeserializationError, match="required field 'message' not found"):
        exceptions.JsonRpcError.from_json({'code': 1})

    with pytest.raises(pjrpc.exc.DeserializationError, match="required field 'code' not found"):
        exceptions.JsonRpcError.from_json({'message': ""})

    with pytest.raises(pjrpc.exc.DeserializationError, match="field 'code' must be of type integer"):
        exceptions.JsonRpcError.from_json({'code': "1", 'message': ""})

    with pytest.raises(pjrpc.exc.DeserializationError, match="field 'message' must be of type string"):
        exceptions.JsonRpcError.from_json({'code': 1, 'message': 2})


def test_error_repr():
    assert repr(exceptions.ServerError()) == "ServerError(code=-32000, message='Server error')"
    assert str(exceptions.ServerError()) == "(-32000) Server error"


def test_custom_error_registration():
    data = {
        'code': 2000,
        'message': 'Custom error',
        'data': 'custom_data',
    }

    class CustomError(exceptions.TypedError):
        CODE = 2000
        MESSAGE = 'Custom error'

    error = exceptions.JsonRpcError.from_json(data)

    assert isinstance(error, CustomError)
    assert error.code == 2000
    assert error.message == 'Custom error'
    assert error.data == 'custom_data'
