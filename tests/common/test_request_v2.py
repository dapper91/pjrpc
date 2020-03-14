import pytest

import pjrpc
from pjrpc.common import v20, exceptions


@pytest.mark.parametrize(
    'id, params', [
        (1, []),
        ('1', []),
        (None, []),
        (1, None),
        (1, []),
        (1, [1, 2]),
        (1, {'a': 1, 'b': 2}),
    ],
)
def test_request_serialization(id, params):
    request = v20.Request('method', params, id=id)

    actual_dict = request.to_json()
    expected_dict = {
        'jsonrpc': '2.0',
        'method': 'method',
    }
    if id is not None:
        expected_dict.update(id=id)
    if params:
        expected_dict.update(params=params)

    assert actual_dict == expected_dict


@pytest.mark.parametrize(
    'id, params', [
        (1, []),
        ('1', []),
        (None, []),
        (1, None),
        (1, []),
        (1, [1, 2]),
        (1, {'a': 1, 'b': 2}),
    ],
)
def test_request_deserialization(id, params):
    data = {
        'jsonrpc': '2.0',
        'id': id,
        'method': 'method',
    }
    if params:
        data.update(params=params)

    request = v20.Request.from_json(data)

    assert request.id == id
    assert request.method == 'method'
    if params:
        assert request.params == params


def test_request_properties():
    request = v20.Request('method')

    assert request.is_notification is True


def test_request_repr():
    request = v20.Request(method='method', params={'a': 1, 'b': 2})
    assert str(request) == "method(a=1,b=2)"
    assert repr(request) == "Request(method='method', params={'a': 1, 'b': 2}, id=None)"

    request = v20.Request(method='method', params=[1, 2], id=1)
    assert str(request) == "method(1, 2)"
    assert repr(request) == "Request(method='method', params=[1, 2], id=1)"


def test_request_deserialization_error():
    with pytest.raises(pjrpc.exc.DeserializationError, match="data must be of type dict"):
        v20.Request.from_json([])

    with pytest.raises(pjrpc.exc.DeserializationError, match="required field 'jsonrpc' not found"):
        v20.Request.from_json({})

    with pytest.raises(pjrpc.exc.DeserializationError, match="jsonrpc version '2.1' is not supported"):
        v20.Request.from_json({'jsonrpc': '2.1'})

    with pytest.raises(pjrpc.exc.DeserializationError, match="field 'id' must be of type integer or string"):
        v20.Request.from_json({'jsonrpc': '2.0', 'id': {}})

    with pytest.raises(pjrpc.exc.DeserializationError, match="field 'method' must be of type string"):
        v20.Request.from_json({'jsonrpc': '2.0', 'id': 1, 'method': 1})

    with pytest.raises(pjrpc.exc.DeserializationError, match="field 'params' must be of type list or dict"):
        v20.Request.from_json({'jsonrpc': '2.0', 'id': 1, 'method': 'method', 'params': 'params'})


def test_batch_request_serialization():
    request = v20.BatchRequest(
        v20.Request('method0', [], id=None),
        v20.Request('method1', [1, 2], id=1),
        v20.Request('method2', {'a': 1, 'b': 2}, id=None),
    )

    actual_dict = request.to_json()
    expected_dict = [
        {
            'jsonrpc': '2.0',
            'method': 'method0',
        },
        {
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'method1',
            'params': [1, 2],
        },
        {
            'jsonrpc': '2.0',
            'method': 'method2',
            'params': {'a': 1, 'b': 2},
        },
    ]

    assert actual_dict == expected_dict


def test_batch_request_deserialization():
    data = [
        {
            'jsonrpc': '2.0',
            'id': None,
            'method': 'method0',
            'params': [],
        },
        {
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'method1',
            'params': [1, 2],
        },
        {
            'jsonrpc': '2.0',
            'id': None,
            'method': 'method2',
            'params': {'a': 1, 'b': 2},
        },
    ]

    request = v20.BatchRequest.from_json(data)

    assert request[0].id is None
    assert request[0].method == 'method0'
    assert request[0].params == []

    assert request[1].id == 1
    assert request[1].method == 'method1'
    assert request[1].params == [1, 2]

    assert request[2].id is None
    assert request[2].method == 'method2'
    assert request[2].params == {'a': 1, 'b': 2}


def test_batch_request_methods():
    request = v20.BatchRequest(
        v20.Request('method1', [1], id=None),
        v20.Request('method2', [1], id=None),
        v20.Request('method3', [1], id=1),
    )
    assert len(request) == 3
    assert not request.is_notification

    request.append(v20.Request('method4', [2], id=2))
    assert len(request) == 4

    request.extend([
        v20.Request('method5', [3], id=3),
        v20.Request('method6', [4], id=4),
    ])
    assert len(request) == 6

    request = v20.BatchRequest(
        v20.Request(id=None, method='method1'),
        v20.Request(id=None, method='method2'),
    )

    assert request.is_notification


def test_batch_request_errors():
    with pytest.raises(exceptions.IdentityError):
        v20.BatchRequest(
            v20.Request(id=1, method='method'),
            v20.Request(id=1, method='method'),
        )


def test_batch_request_repr():
    request = v20.BatchRequest(
        v20.Request('method1', [1, 2]),
        v20.Request('method2', {'a': 1, 'b': 2}, id='2'),
    )

    assert str(request) == "[method1(1, 2), method2(a=1,b=2)]"
    assert repr(request) == "BatchRequest(Request(method='method1', params=[1, 2], id=None)," \
                            "Request(method='method2', params={'a': 1, 'b': 2}, id='2'))"


def test_batch_request_deserialization_error():
    with pytest.raises(pjrpc.exc.DeserializationError, match="data must be of type list"):
        v20.BatchRequest.from_json({})
