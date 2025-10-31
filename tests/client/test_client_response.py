from pjrpc.client import exceptions
from pjrpc.common import BatchResponse, Response


def test_response_error_serialization():
    response = Response(error=exceptions.MethodNotFoundError())
    actual_dict = response.to_json()
    expected_dict = {
        'jsonrpc': '2.0',
        'id': None,
        'error': {
            'code': -32601,
            'message': 'Method not found',
        },
    }

    assert actual_dict == expected_dict


def test_batch_response_error_serialization():
    response = BatchResponse(error=exceptions.MethodNotFoundError())
    actual_dict = response.to_json()
    expected_dict = {
        'jsonrpc': '2.0',
        'id': None,
        'error': {
            'code': -32601,
            'message': 'Method not found',
        },
    }

    assert actual_dict == expected_dict


def test_response_error_deserialization():
    data = {
        'jsonrpc': '2.0',
        'id': None,
        'error': {
            'code': -32601,
            'message': 'Method not found',
        },
    }
    response = Response.from_json(data, error_cls=exceptions.JsonRpcError)

    assert response.is_error
    assert response.error == exceptions.MethodNotFoundError()


def test_batch_response_error_deserialization():
    data = {
        'jsonrpc': '2.0',
        'id': None,
        'error': {
            'code': -32601,
            'message': 'Method not found',
        },
    }
    response = BatchResponse.from_json(data, error_cls=exceptions.JsonRpcError)

    assert response.is_error
    assert response.error == exceptions.MethodNotFoundError()
