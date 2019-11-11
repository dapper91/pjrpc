"""
JSON-RPC version 2.0 protocol implementation.
"""

import operator as op
import functools as ft

from .exceptions import DeserializationError, JsonRpcError, IdentityError
from .common import UNSET


class Response:
    """
    JSON-RPC version 2.0 response.

    :param id: response identifier
    :param result: response result
    :param error: response error
    """

    version = '2.0'

    @classmethod
    def from_json(cls, json_data, error_cls=JsonRpcError):
        """
        Deserializes a response from json data.

        :param json_data: data the response to be deserialized from
        :param error_cls: error class
        :returns: response object
        :raises: :py:class:`pjrpc.common.exception.DeserializationError` if format is incorrect
        """

        try:
            if not isinstance(json_data, dict):
                raise DeserializationError(f"data must be of type dict")

            jsonrpc = json_data['jsonrpc']
            if jsonrpc != cls.version:
                raise DeserializationError(f"jsonrpc version '{json_data['jsonrpc']}' is not supported")

            id = json_data.get('id')
            if id is not None and not isinstance(id, (int, str)):
                raise DeserializationError("field 'id' must be of type integer or string")

            error = json_data.get('error', UNSET)
            if error is not UNSET:
                error = error_cls.from_json(error)

            result = json_data.get('result', UNSET)
            if result is UNSET and error is UNSET:
                raise DeserializationError("'result' or 'error' fields must be provided")
            if result and error:
                raise DeserializationError("'result' and 'error' fields are mutually exclusive")

            return cls(id=id, result=result, error=error)
        except KeyError as e:
            raise DeserializationError(f"required field {e} not found") from e

    @property
    def id(self):
        """
        Response identifier.
        """

        return self._id

    @property
    def result(self):
        """
        Response result. If the response has not succeeded raises an exception deserialized from the `error` field.
        """

        if self._error is not UNSET:
            raise self._error

        return self._result

    @property
    def error(self):
        """
        Response error. If the response has succeeded returns :py:data:`pjrpc.common.UNSET`.
        """

        return self._error

    @property
    def is_success(self):
        """
        Returns ``True`` if the response has succeeded.
        """

        return self._error is UNSET

    @property
    def is_error(self):
        """
        Returns ``True`` if the response has not succeeded.
        """

        return not self.is_success

    @property
    def related(self):
        """
        Returns the request related response object if the response has been
        received from the server otherwise returns ``None``.
        """

        return self._related

    @related.setter
    def related(self, request):
        """
        Sets a related request object.
        """

        self._related = request

    def __init__(self, id, result=UNSET, error=UNSET):
        assert result is not UNSET or error is not UNSET, "result or error argument must be provided"
        assert result is UNSET or error is UNSET, "result and error arguments are mutually exclusive"

        self._id = id
        self._result = result
        self._error = error
        self._related = None

    def __str__(self):
        return f"{self.result if self.is_success else self.error}"

    def __repr__(self):
        return "{class_name}(id={id}, result={result}, error={error})".format(
            class_name=self.__class__.__name__, id=self._id, result=repr(self._result), error=repr(self._error),
        )

    def to_json(self):
        """
        Serializes the response to json data.

        :returns: json data
        """

        json_data = {
            'jsonrpc': self.version,
            'id': self._id,
        }
        if self._result is not UNSET:
            json_data.update(result=self.result)
        if self._error is not UNSET:
            json_data.update(error=self.error.to_json())

        return json_data


class Request:
    """
    JSON-RPC version 2.0 request.

    :param method: method name
    :param params: method parameters
    :param id: request identifier
    """

    version = '2.0'

    @classmethod
    def from_json(cls, json_data):
        """
        Deserializes a request from json data.

        :param json_data: data the request to be deserialized from
        :returns: request object
        :raises: :py:class:`pjrpc.common.exception.DeserializationError` if format is incorrect
        """

        try:
            if not isinstance(json_data, dict):
                raise DeserializationError(f"data must be of type dict")

            jsonrpc = json_data['jsonrpc']
            if jsonrpc != cls.version:
                raise DeserializationError(f"jsonrpc version '{json_data['jsonrpc']}' is not supported")

            id = json_data.get('id')
            if id is not None and not isinstance(id, (int, str)):
                raise DeserializationError(f"field 'id' must be of type integer or string")

            method = json_data['method']
            if not isinstance(method, str):
                raise DeserializationError(f"field 'method' must be of type string")

            params = json_data.get('params', [])
            if not isinstance(params, (list, dict)):
                raise DeserializationError(f"field 'params' must be of type list or dict")

            return cls(method, params, id)
        except KeyError as e:
            raise DeserializationError(f"required field {e} not found") from e

    @property
    def id(self):
        """
        Request identifier.
        """

        return self._id

    @property
    def method(self):
        """
        Request method name.
        """

        return self._method

    @property
    def params(self):
        """
        Request method parameters.
        """

        return self._params

    def __init__(self, method, params=None, id=None):
        self._method = method
        self._params = params
        self._id = id

    def __str__(self):
        if isinstance(self.params, list):
            params = ', '.join(map(str, self.params))
        else:
            params = ','.join(f"{k}={v}" for k, v in self.params.items())

        return f"{self.method}({params})"

    def __repr__(self):
        return "{class_name}(method={method}, params={params}, id={id})".format(
            class_name=self.__class__.__name__, method=repr(self._method), params=repr(self._params), id=repr(self._id),
        )

    def to_json(self):
        """
        Serializes the request to json data.

        :returns: json data
        """

        json_data = {
            'jsonrpc': self.version,
            'method': self._method,
        }
        if self._id is not None:
            json_data.update(id=self._id)
        if self.params:
            json_data.update(params=self._params)

        return json_data

    @property
    def is_notification(self):
        """
        Returns ``True`` if the request is a notification e.g. `id` is ``None``.
        """

        return self.id is None


class BatchResponse:
    """
    JSON-RPC 2.0 batch response.

    :param responses: responses to be added to the batch
    :param strict: if ``True`` checks response identifier uniqueness
    """

    version = '2.0'

    @classmethod
    def from_json(cls, json_data, error_cls=JsonRpcError):
        """
        Deserializes a batch response from json data.

        :param json_data: data the response to be deserialized from
        :param error_cls: error class
        :returns: batch response object
        """

        try:
            if isinstance(json_data, dict):
                jsonrpc = json_data['jsonrpc']
                if jsonrpc != cls.version:
                    raise DeserializationError(f"jsonrpc version '{json_data['jsonrpc']}' is not supported")

                id, error = json_data.get('id'), json_data.get('error', UNSET)
                if id is None and error is not UNSET:
                    return cls(error=error_cls.from_json(json_data['error']))

            if not isinstance(json_data, (list, tuple)):
                raise DeserializationError(f"data must be of type list")

        except KeyError as e:
            raise DeserializationError(f"required field {e} not found") from e

        return cls(*(Response.from_json(item) for item in json_data))

    @property
    def error(self):
        """
        Response error. If the response has succeeded returns :py:data:`pjrpc.common.UNSET`.
        """

        return self._error

    @property
    def is_success(self):
        """
        Returns ``True`` if the response has succeeded.
        """

        return self._error is UNSET

    @property
    def is_error(self):
        """
        Returns ``True`` if the request has not succeeded. Note that it is not the same as
        :py:attr:`pjrpc.common.BatchResponse.has_error`. `is_error` indicates that the batch request failed
        at all, while `has_error` indicates that one of the requests in the batch failed.
        """

        return not self.is_success

    @property
    def has_error(self):
        """
        Returns ``True`` if any response has an error.
        """

        return any((response.is_error for response in self._responses))

    @property
    def result(self):
        """
        Returns the batch result as a tuple. If any response of the batch has an error
        raises an exception of the first errored response.
        """

        if self.is_error:
            raise self._error

        result = []

        for response in self._responses:
            if response.is_error:
                raise response.error
            result.append(response.result)

        return tuple(result)

    @property
    def related(self):
        """
        Returns the request related response object if the response has been
        received from the server otherwise returns ``None``.
        """

        return self._related

    @related.setter
    def related(self, request):
        """
        Sets related request object.
        """

        self._related = request

    def __init__(self, *responses, error=UNSET, strict=True):
        self._responses = []
        self._ids = set()
        self._related = None
        self._error = error
        self._strict = strict

        self.extend(responses)

    def __repr__(self):
        return f"{self.__class__.__name__}({','.join(map(repr, self._responses))}, error={repr(self._error)})"

    def __str__(self):
        return f"[{', '.join(map(str, self._responses))}]" if self.is_success else self.error

    def __getitem__(self, idx):
        """
        Returns a request at index `idx`.
        """

        return self._responses[idx]

    def __iter__(self):
        return iter(self._responses)

    def __len__(self):
        return len(self._responses)

    def append(self, response):
        """
        Appends a response to the batch.
        """

        self._add_ids(response.id)
        self._responses.append(response)

    def extend(self, responses):
        """
        Extends the batch with the `responses`.
        """

        self._add_ids(*(resp.id for resp in responses))
        self._responses.extend(responses)

    def to_json(self):
        """
        Serializes the batch response to json data.

        :returns: json data
        """

        if self.is_error:
            return Response(id=None, error=self.error).to_json()

        return [response.to_json() for response in self._responses]

    def _add_ids(self, *ids):
        if self._strict:
            new_ids = self._ids.copy()

            for id in filter(ft.partial(op.is_not, None), ids):
                if id in new_ids:
                    raise IdentityError(f"response id duplicates found: {id}")
                else:
                    new_ids.add(id)

            self._ids = new_ids


class BatchRequest:
    """
    JSON-RPC 2.0 batch request.

    :param requests: requests to be added to the batch
    :param strict: if ``True`` checks response identifier uniqueness
    """

    version = '2.0'

    @classmethod
    def from_json(cls, data):
        """
        Deserializes a batch request from json data.

        :param data: data the request to be deserialized from
        :returns: batch request object
        """

        if not isinstance(data, (list, tuple)):
            raise DeserializationError(f"data must be of type list")

        if len(data) == 0:
            raise DeserializationError(f"request list is empty")

        return cls(*(Request.from_json(request) for request in data))

    def __init__(self, *requests, strict=True):
        self._requests = []
        self._ids = set()
        self._strict = strict
        self.extend(requests)

    def __repr__(self):
        return f"{self.__class__.__name__}({','.join(map(repr, self._requests))})"

    def __str__(self):
        return f"[{', '.join(map(str, self._requests))}]"

    def __getitem__(self, idx):
        """
        Returns a request at index `idx`.
        """

        return self._requests[idx]

    def __iter__(self):
        return iter(self._requests)

    def __len__(self):
        return len(self._requests)

    def append(self, request):
        """
        Appends a request to the batch.
        """

        self._add_ids(request.id)
        self._requests.append(request)

    def extend(self, requests):
        """
        Extends a batch with `requests`.
        """

        self._add_ids(*(resp.id for resp in requests))
        self._requests.extend(requests)

    def to_json(self):
        """
        Serializes the request to json data.

        :returns: json data
        """

        return [request.to_json() for request in self._requests]

    @property
    def is_notification(self):
        """
        Returns ``True`` if all the request in the batch are notifications.
        """

        return all(map(op.attrgetter('is_notification'), self._requests))

    def _add_ids(self, *ids):
        if self._strict:
            new_ids = self._ids.copy()

            for id in filter(ft.partial(op.is_not, None), ids):
                if id in new_ids:
                    raise IdentityError(f"request id duplicates found: {id}")
                else:
                    new_ids.add(id)

            self._ids = new_ids
