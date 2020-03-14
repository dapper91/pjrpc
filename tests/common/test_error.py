import pytest

import pjrpc


def test_error_serialization():
    error = pjrpc.exc.ServerError()

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

    error = pjrpc.exc.ServerError.from_json(data)

    assert error.code == -32000
    assert error.message == 'Server error'


def test_error_data_serialization():
    error = pjrpc.exc.MethodNotFoundError(data='method_name')

    actual_dict = error.to_json()
    expected_dict = {
        'code': -32601,
        'message': 'Method not found',
        'data': 'method_name',
    }

    assert actual_dict == expected_dict


def test_custom_error_data_serialization():
    error = pjrpc.exc.JsonRpcError(code=2001, message='Custom error', data='additional data')

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

    error = pjrpc.exc.JsonRpcError.from_json(data)

    assert error.code == -32601
    assert error.message == 'Method not found'
    assert error.data == 'method_name'


def test_error_deserialization_errors():
    with pytest.raises(pjrpc.exc.DeserializationError, match="data must be of type dict"):
        pjrpc.exc.JsonRpcError.from_json([])

    with pytest.raises(pjrpc.exc.DeserializationError, match="required field 'message' not found"):
        pjrpc.exc.JsonRpcError.from_json({'code': 1})

    with pytest.raises(pjrpc.exc.DeserializationError, match="required field 'code' not found"):
        pjrpc.exc.JsonRpcError.from_json({'message': ""})

    with pytest.raises(pjrpc.exc.DeserializationError, match="field 'code' must be of type integer"):
        pjrpc.exc.JsonRpcError.from_json({'code': "1", 'message': ""})

    with pytest.raises(pjrpc.exc.DeserializationError, match="field 'message' must be of type string"):
        pjrpc.exc.JsonRpcError.from_json({'code': 1, 'message': 2})


def test_error_repr():
    assert repr(pjrpc.exc.ServerError(data='data')) == "ServerError(code=-32000, message='Server error', data='data')"
    assert str(pjrpc.exc.ServerError()) == "(-32000) Server error"


def test_custom_error_registration():
    data = {
        'code': 2000,
        'message': 'Custom error',
        'data': 'custom_data',
    }

    class CustomError(pjrpc.exc.JsonRpcError):
        code = 2000
        message = 'Custom error'

    error = pjrpc.exc.JsonRpcError.from_json(data)

    assert isinstance(error, CustomError)
    assert error.code == 2000
    assert error.message == 'Custom error'
    assert error.data == 'custom_data'
