"""
JSON-RPC version 2.0 protocol response implementation.
"""

import abc
import dataclasses as dc
import itertools as it
import operator as op
from typing import Any, ClassVar, Iterator, Optional, Self

from pjrpc.common.typedefs import JsonRpcRequestIdT

from .common import UNSET, JsonT, MaybeSet
from .exceptions import DeserializationError, IdentityError, JsonRpcError


@dc.dataclass(slots=True, kw_only=True)
class AbstractResponse(abc.ABC):
    """
    JSON-RPC 2.0 abstract response.
    """

    @classmethod
    @abc.abstractmethod
    def from_json(cls, data: JsonT, error_cls: type[JsonRpcError] = JsonRpcError) -> Self:
        pass

    @abc.abstractmethod
    def to_json(self) -> JsonT:
        pass

    @property
    @abc.abstractmethod
    def is_success(self) -> bool:
        pass

    @property
    @abc.abstractmethod
    def is_error(self) -> bool:
        pass

    @abc.abstractmethod
    def unwrap_result(self) -> JsonT:
        pass

    @abc.abstractmethod
    def unwrap_error(self) -> JsonRpcError:
        pass


@dc.dataclass(slots=True)
class Response(AbstractResponse):
    """
    JSON-RPC 2.0 response.

    :param id: response identifier
    :param result: response result
    :param error: response error
    """

    version: ClassVar[str] = '2.0'

    id: Optional[JsonRpcRequestIdT] = None
    result: MaybeSet[JsonT] = UNSET
    error: MaybeSet[JsonRpcError] = UNSET

    @classmethod
    def from_json(cls, data: JsonT, error_cls: type[JsonRpcError] = JsonRpcError) -> Self:
        """
        Deserializes a response from json data.

        :param data: data the response to be deserialized from
        :param error_cls: error class
        :returns: response object
        :raises: :py:class:`pjrpc.common.exceptions.DeserializationError` if format is incorrect
        """

        try:
            if not isinstance(data, dict):
                raise DeserializationError("data must be of type dict")

            jsonrpc = data['jsonrpc']
            if jsonrpc != cls.version:
                raise DeserializationError(f"jsonrpc version '{data['jsonrpc']}' is not supported")

            request_id = data.get('id')
            if request_id is not None and not isinstance(request_id, (int, str)):
                raise DeserializationError("field 'id' must be of type integer or string")

            error_data = data.get('error', UNSET)
            error: MaybeSet[JsonRpcError]
            if error_data is not UNSET:
                if not isinstance(error_data, dict):
                    raise DeserializationError("error must be of type dict")
                error = error_cls.from_json(error_data)
            else:
                error = UNSET

            result = data.get('result', UNSET)
            if result is UNSET and error is UNSET:
                raise DeserializationError("'result' or 'error' fields must be provided")
            if result and error:
                raise DeserializationError("'result' and 'error' fields are mutually exclusive")

            return cls(id=request_id, result=result, error=error)
        except KeyError as e:
            raise DeserializationError(f"required field {e} not found") from e

    def __post_init__(self) -> None:
        assert self.result is not UNSET or self.error is not UNSET, "result or error argument must be provided"
        assert self.result is UNSET or self.error is UNSET, "result and error arguments are mutually exclusive"

    @property
    def is_success(self) -> bool:
        """
        Returns ``True`` if the response has succeeded.
        """

        return self.result is not UNSET

    @property
    def is_error(self) -> bool:
        """
        Returns ``True`` if the response has not succeeded.
        """

        return self.error is not UNSET

    def unwrap_result(self) -> JsonT:
        """
        Returns result. If result is not set raises and exception.
        """

        if self.is_error:
            raise self.unwrap_error()

        assert self.result is not UNSET, "result is not set"
        return self.result

    def unwrap_error(self) -> JsonRpcError:
        """
        Returns error. If error is not set raises and exception.
        """

        assert self.error is not UNSET, "error is not set"
        return self.error

    def to_json(self) -> JsonT:
        """
        Serializes the response to json data.

        :returns: json data
        """

        data: dict[str, JsonT] = {
            'jsonrpc': self.version,
            'id': self.id,
        }
        if self.result is not UNSET:
            data.update(result=self.result)
        if self.error is not UNSET:
            data.update(error=self.error.to_json())

        return data


@dc.dataclass(slots=True)
class BatchResponse(AbstractResponse):
    """
    JSON-RPC 2.0 batch response.

    :param responses: responses to be added to the batch
    """

    version: ClassVar[str] = '2.0'

    responses: MaybeSet[tuple[Response, ...]] = UNSET
    error: MaybeSet[JsonRpcError] = UNSET

    @classmethod
    def from_json(
            cls,
            data: JsonT,
            error_cls: type[JsonRpcError] = JsonRpcError,
            check_ids: bool = True,
    ) -> Self:
        """
        Deserializes a batch response from json data.

        :param data: data the response to be deserialized from
        :param error_cls: error class
        :param check_ids: check response ids for uniqueness
        :returns: batch response object
        """

        try:
            if isinstance(data, dict):
                jsonrpc = data['jsonrpc']
                if not isinstance(jsonrpc, str):
                    raise DeserializationError("field 'jsonrpc' must be of type string")

                if jsonrpc != cls.version:
                    raise DeserializationError(f"jsonrpc version '{data['jsonrpc']}' is not supported")

                request_id, error = data.get('id'), data.get('error', UNSET)
                if request_id is None and error is not UNSET:
                    return cls(responses=(), error=error_cls.from_json(error))

            if not isinstance(data, (list, tuple)):
                raise DeserializationError("data must be of type list")

        except KeyError as e:
            raise DeserializationError(f"required field {e} not found") from e

        responses = tuple(Response.from_json(item) for item in data)
        if check_ids:
            cls._check_response_id_uniqueness(responses)

        return cls(responses=responses)

    def to_json(self) -> JsonT:
        """
        Serializes the batch response to json data.

        :returns: json data
        """

        if self.is_error:
            return Response(id=None, error=self.error, result=UNSET).to_json()

        return [response.to_json() for response in self.responses or ()]

    def __getitem__(self, idx: int) -> Response:
        """
        Returns a request at index `idx`.
        """

        if not self.responses:
            raise IndexError("index out of range")

        return self.responses[idx]

    def __iter__(self) -> Iterator[Response]:
        return iter(self.responses or ())

    def __len__(self) -> int:
        return len(self.responses or ())

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, BatchResponse):
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
    def is_success(self) -> bool:
        """
        Returns ``True`` if the response has succeeded.
        """

        return self.error is UNSET

    @property
    def is_error(self) -> bool:
        """
        Returns ``True`` if the request has not succeeded. Note that it is not the same as
        :py:attr:`pjrpc.common.BatchResponse.has_error`. `is_error` indicates that the whole batch request failed,
        whereas `has_error` indicates that one of the requests in the batch failed.
        """

        return not self.is_success

    @property
    def has_error(self) -> bool:
        """
        Returns ``True`` if any response has an error.
        """

        return any((response.is_error for response in self.responses or ()))

    def unwrap_results(self) -> tuple[MaybeSet[JsonT], ...]:
        """
        Returns the batch result as a tuple. If any response of the batch has an error
        raises an exception related to the first errored response.
        """

        if self.is_error:
            raise self.unwrap_error()

        result = []

        for response in self.responses or ():
            if response.is_error:
                raise response.unwrap_error()
            result.append(response.result)

        return tuple(result)

    def unwrap_result(self) -> JsonT:
        """
        Returns result. If result is not set raises and exception.
        """

        return self.unwrap_results()

    def unwrap_error(self) -> JsonRpcError:
        """
        Returns error. If error is not set raises and exception.
        """

        assert self.error is not UNSET, "error is not set"
        return self.error

    @classmethod
    def _check_response_id_uniqueness(cls, responses: tuple[Response, ...]) -> None:
        ids = tuple(response.id for response in responses if response.id is not None)
        if len(ids) != len(set(ids)):
            raise IdentityError("batch response ids are not unique")
