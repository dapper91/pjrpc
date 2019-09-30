import pytest
from pjrpc.common import v20, exceptions


@pytest.mark.parametrize('id, result', [
    (1, None),
    ('1', None),
    (None, None),
    (1, 'result'),
    (1, {'key': 'value'}),
    (1, [1, 2]),
    (1, None),
])
def test_response_serialization(id, result):
    response = v20.Response(id=id, result=result)

    actual_dict = response.to_json()
    expected_dict = {
        'jsonrpc': '2.0',
        'id': id,
        'result': result,
    }

    assert actual_dict == expected_dict


@pytest.mark.parametrize('id, result', [
    (1, None),
    ('1', None),
    (None, None),
    (1, 'result'),
    (1, {'key': 'value'}),
    (1, [1, 2]),
    (1, None),
])
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


def test_batch_response_serialization():
    response = v20.BatchResponse(
        v20.Response(id=None, result='result0'),
        v20.Response(id=1, result='result1'),
        v20.Response(id=2, result='result2'),
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
            'id': 2,
            'result': 'result2',
        },
    ]

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
            'id': 2,
            'result': 'result2',
        },
    ]

    response = v20.BatchResponse.from_json(data)

    assert response[0].id is None
    assert response[0].result == 'result0'

    assert response[1].id == 1
    assert response[1].result == 'result1'

    assert response[2].id == 2
    assert response[2].result == 'result2'


def test_batch_response_methods():
    request = v20.BatchResponse(
        v20.Response(id=None, result='result0'),
        v20.Response(id=None, result='result0'),
        v20.Response(id=1, result='result1'),
    )
    request.append(v20.Response(id=2, result='result2'))
    request.extend([
        v20.Response(id=3, result='result3'),
        v20.Response(id=4, result='result4'),
    ])


def test_batch_response_errors():
    with pytest.raises(exceptions.IdentityError):
        v20.BatchResponse(
            v20.Response(id=1, result='result1'),
            v20.Response(id=1, result='result1'),
        )
