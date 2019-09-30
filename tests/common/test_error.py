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
        'data': 'method_name'
    }

    assert actual_dict == expected_dict


def test_custom_error_data_serialization():
    error = pjrpc.exc.JsonRpcError(code=2001, message='Custom error', data='method_name')

    actual_dict = error.to_json()
    expected_dict = {
        'code': 2001,
        'message': 'Custom error',
        'data': 'method_name'
    }

    assert actual_dict == expected_dict


def test_custom_error_data_deserialization():
    data = {
        'code': -32601,
        'message': 'Method not found',
        'data': 'method_name'
    }

    error = pjrpc.exc.JsonRpcError.from_json(data)

    assert error.code == -32601
    assert error.message == 'Method not found'
    assert error.data == 'method_name'


def test_custom_error_registration():
    data = {
        'code': 2000,
        'message': 'Custom error',
        'data': 'custom_data'
    }

    class CustomError(pjrpc.exc.JsonRpcError):
        code = 2000
        message = 'Custom error'

    error = pjrpc.exc.JsonRpcError.from_json(data)

    assert isinstance(error, CustomError)
    assert error.code == 2000
    assert error.message == 'Custom error'
    assert error.data == 'custom_data'
