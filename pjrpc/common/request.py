"""
JSON-RPC version 2.0 protocol request implementation.
"""

import abc
import dataclasses as dc
import itertools as it
import operator as op
from typing import Any, ClassVar, Iterator, Optional, Self

from pjrpc.common.typedefs import JsonRpcParamsT, JsonRpcRequestIdT

from .common import JsonT
from .exceptions import DeserializationError, IdentityError


@dc.dataclass(slots=True, kw_only=True)
class AbstractRequest(abc.ABC):
    """
    JSON-RPC 2.0 abstract request.
    """

    @classmethod
    @abc.abstractmethod
    def from_json(cls, data: JsonT) -> Self:
        pass

    @abc.abstractmethod
    def to_json(self) -> JsonT:
        pass

    @property
    @abc.abstractmethod
    def is_notification(self) -> bool:
        pass


@dc.dataclass(slots=True)
class Request(AbstractRequest):
    """
    JSON-RPC 2.0 request.

    :param method: method name
    :param params: method parameters
    :param id: request identifier
    """

    version: ClassVar[str] = '2.0'

    method: str
    params: Optional[JsonRpcParamsT] = None
    id: Optional[JsonRpcRequestIdT] = None

    @classmethod
    def from_json(cls, data: JsonT) -> Self:
        """
        Deserializes a request from json data.

        :param data: data the request to be deserialized from
        :returns: request object
        :raises: :py:class:`pjrpc.common.exceptions.DeserializationError` if format is incorrect
        """

        try:
            if not isinstance(data, dict):
                raise DeserializationError("data must be of type dict")

            jsonrpc = data['jsonrpc']
            if not isinstance(jsonrpc, str):
                raise DeserializationError("field 'jsonrpc' must be of type string")

            if jsonrpc != cls.version:
                raise DeserializationError(f"jsonrpc version '{data['jsonrpc']}' is not supported")

            request_id = data.get('id')
            if request_id is not None and not isinstance(request_id, (int, str)):
                raise DeserializationError("field 'id' must be of type integer or string")

            method = data['method']
            if not isinstance(method, str):
                raise DeserializationError("field 'method' must be of type string")

            params = data.get('params', {})
            if not isinstance(params, (list, dict)):
                raise DeserializationError("field 'params' must be of type list or dict")

            return cls(id=request_id, method=method, params=params)
        except KeyError as e:
            raise DeserializationError(f"required field {e} not found") from e

    def to_json(self) -> JsonT:
        """
        Serializes the request to json data.

        :returns: json data
        """

        data: dict[str, JsonT] = {
            'jsonrpc': self.version,
            'method': self.method,
        }
        if self.id is not None:
            data.update(id=self.id)
        if self.params:
            data.update(params=self.params)

        return data

    @property
    def is_notification(self) -> bool:
        """
        Returns ``True`` if the request is a notification e.g. response will not be sent.
        """

        return self.id is None


@dc.dataclass(slots=True)
class BatchRequest(AbstractRequest):
    """
    JSON-RPC 2.0 batch request.

    :param requests: requests to be added to the batch
    """

    version: ClassVar[str] = '2.0'

    requests: tuple[Request, ...]

    def __init__(self, *requests: Request) -> None:
        self.requests = tuple(requests)

    @classmethod
    def from_json(cls, data: JsonT, check_ids: bool = True) -> Self:
        """
        Deserializes a batch request from json data.

        :param data: data the request to be deserialized from
        :param check_ids: check response ids for uniqueness
        :returns: batch request object
        """

        if not isinstance(data, (list, tuple)):
            raise DeserializationError("data must be of type list")

        if len(data) == 0:
            raise DeserializationError("request list is empty")

        requests = tuple(Request.from_json(request) for request in data)
        if check_ids:
            cls._check_response_id_uniqueness(requests)

        return cls(*requests)

    def to_json(self) -> JsonT:
        """
        Serializes the request to json data.

        :returns: json data
        """

        return [request.to_json() for request in self.requests]

    def __getitem__(self, idx: int) -> Request:
        """
        Returns a request at index `idx`.
        """

        return self.requests[idx]

    def __iter__(self) -> Iterator[Request]:
        return iter(self.requests)

    def __len__(self) -> int:
        return len(self.requests)

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, BatchRequest):
            return NotImplemented

        return all(
            it.starmap(
                op.eq, zip(
                    sorted(self, key=op.attrgetter('id')),
                    sorted(other, key=op.attrgetter('id')),
                ),
            ),
        )

    @property
    def is_notification(self) -> bool:
        """
        Returns ``True`` if all requests in the batch are notifications.
        """

        return all(map(op.attrgetter('is_notification'), self.requests))

    @classmethod
    def _check_response_id_uniqueness(cls, requests: tuple[Request, ...]) -> None:
        ids = tuple(request.id for request in requests if request.id is not None)
        if len(ids) != len(set(ids)):
            raise IdentityError("batch request ids are not unique")
