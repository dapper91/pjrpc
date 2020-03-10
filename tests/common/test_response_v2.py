import pytest

import pjrpc
from pjrpc.common import v20, exceptions


@pytest.mark.parametrize(
    'id, result', [
        (1, None),
        ('1', None),
        (None, None),
        (1, 'result'),
        (1, {'key': 'value'}),
        (1, [1, 2]),
        (1, None),
    ],
)
def test_response_serialization(id, result):
    response = v20.Response(id=id, result=result)

    actual_dict = response.to_json()
    expected_dict = {
        'jsonrpc': '2.0',
        'id': id,
        'result': result,
    }

    assert actual_dict == expected_dict


@pytest.mark.parametrize(
    'id, result', [
        (1, None),
        ('1', None),
        (None, None),
        (1, 'result'),
        (1, {'key': 'value'}),
        (1, [1, 2]),
        (1, None),
    ],
)
def test_response_deserialization(id, result):
    data = {
        'jsonrpc': '2.0',
        'id': id,
        'result': result,
    }

    response = v20.Response.from_json(data)

    assert response.id == id
    assert response.result == result


def test_response_properties():
    response = v20.Response(id=None, result='result')

    assert response.is_success is True
    assert response.is_error is False

    response = v20.Response(id=None, error='error')

    assert response.is_success is False
    assert response.is_error is True


def test_response_repr():
    response = v20.Response(id=1, result='result1')
    assert str(response) == "result1"
    assert repr(response) == "Response(id=1, result='result1', error=UNSET)"


def test_response_deserialization_error():
    with pytest.raises(pjrpc.exc.DeserializationError, match="data must be of type dict"):
        v20.Response.from_json([])

    with pytest.raises(pjrpc.exc.DeserializationError, match="required field 'jsonrpc' not found"):
        v20.Response.from_json({})

    with pytest.raises(pjrpc.exc.DeserializationError, match="jsonrpc version '2.1' is not supported"):
        v20.Response.from_json({'jsonrpc': '2.1'})

    with pytest.raises(pjrpc.exc.DeserializationError, match="field 'id' must be of type integer or string"):
        v20.Response.from_json({'jsonrpc': '2.0', 'id': {}})

    with pytest.raises(pjrpc.exc.DeserializationError, match="'result' or 'error' fields must be provided"):
        v20.Response.from_json({'jsonrpc': '2.0', 'id': 1})

    with pytest.raises(pjrpc.exc.DeserializationError, match="'result' and 'error' fields are mutually exclusive"):
        v20.Response.from_json({'jsonrpc': '2.0', 'id': 1, 'error': {'code': 1, 'message': 'message'}, 'result': 1})


def test_batch_response_serialization():
    response = v20.BatchResponse(
        v20.Response(id=None, result='result0'),
        v20.Response(id=1, result='result1'),
        v20.Response(id=None, result='result2'),
    )

    actual_dict = response.to_json()
    expected_dict = [
        {
            'jsonrpc': '2.0',
            'id': None,
            'result': 'result0',
        },
        {
            'jsonrpc': '2.0',
            'id': 1,
            'result': 'result1',
        },
        {
            'jsonrpc': '2.0',
            'id': None,
            'result': 'result2',
        },
    ]

    assert actual_dict == expected_dict

    response = v20.BatchResponse(error=pjrpc.exc.MethodNotFoundError())
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


def test_batch_response_deserialization():
    data = [
        {
            'jsonrpc': '2.0',
            'id': None,
            'result': 'result0',
        },
        {
            'jsonrpc': '2.0',
            'id': 1,
            'result': 'result1',
        },
        {
            'jsonrpc': '2.0',
            'id': None,
            'result': 'result2',
        },
    ]

    response = v20.BatchResponse.from_json(data)

    assert response[0].id is None
    assert response[0].result == 'result0'

    assert response[1].id == 1
    assert response[1].result == 'result1'

    assert response[2].id is None
    assert response[2].result == 'result2'

    data = {
        'jsonrpc': '2.0',
        'id': None,
        'error': {
            'code': -32601,
            'message': 'Method not found',
        },
    }
    response = v20.BatchResponse.from_json(data)

    assert response.is_error
    assert response.error == pjrpc.exc.MethodNotFoundError()


def test_batch_response_methods():
    response = v20.BatchResponse(
        v20.Response(id=None, result='result0'),
        v20.Response(id=None, result='result0'),
        v20.Response(id=1, result='result1'),
    )
    assert len(response) == 3

    response.append(v20.Response(id=2, result='result2'))
    assert len(response) == 4

    response.extend([
        v20.Response(id=3, result='result3'),
        v20.Response(id=4, result='result4'),
    ])
    assert len(response) == 6

    assert not response.has_error

    response.append(v20.Response(id=5, error=pjrpc.exc.JsonRpcError(code=1, message='msg')))
    assert response.has_error
    with pytest.raises(pjrpc.exc.JsonRpcError) as e:
        response.result

    assert e.value.code == 1
    assert e.value.message == 'msg'


def test_batch_response_errors():
    with pytest.raises(exceptions.IdentityError):
        v20.BatchResponse(
            v20.Response(id=1, result='result1'),
            v20.Response(id=1, result='result1'),
        )


def test_batch_response_repr():
    response = v20.BatchResponse(
        v20.Response(id=None, result='result0'),
        v20.Response(id=1, result='result1'),
    )

    assert str(response) == "[result0, result1]"
    assert repr(response) == "BatchResponse(Response(id=None, result='result0', error=UNSET)," \
                             "Response(id=1, result='result1', error=UNSET), error=UNSET)"


def test_batch_response_deserialization_error():
    with pytest.raises(pjrpc.exc.DeserializationError, match="data must be of type list"):
        v20.BatchResponse.from_json('')
