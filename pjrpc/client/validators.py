from typing import Any, Mapping, Optional

from pjrpc.client import exceptions
from pjrpc.client.client import AsyncMiddlewareHandler, MiddlewareHandler
from pjrpc.common import AbstractRequest, AbstractResponse, BatchRequest, BatchResponse, Request, Response


def validate_response_id_middleware(
    request: AbstractRequest,
    request_kwargs: Mapping[str, Any],
    /,
    handler: MiddlewareHandler,
) -> Optional[AbstractResponse]:
    response = handler(request, request_kwargs)
    if response is not None:
        _validate_any_response_id(request, response)

    return response


async def async_validate_response_id_middleware(
    request: AbstractRequest,
    request_kwargs: Mapping[str, Any],
    /,
    handler: AsyncMiddlewareHandler,
) -> Optional[AbstractResponse]:
    response = await handler(request, request_kwargs)
    if response is not None:
        _validate_any_response_id(request, response)

    return response


def _validate_any_response_id(request: AbstractRequest, response: AbstractResponse) -> None:
    if isinstance(request, Request) and isinstance(response, Response):
        _validate_response_id(request, response)
    elif isinstance(request, BatchRequest) and isinstance(response, BatchResponse):
        _validate_batch_response_ids(request, response)


def _validate_response_id(request: Request, response: Response) -> None:
    if response.id is not None and response.id != request.id:
        raise exceptions.IdentityError(
            f"response id doesn't match the request one: expected {request.id}, got {response.id}",
        )


def _validate_batch_response_ids(batch_request: BatchRequest, batch_response: BatchResponse) -> None:
    if batch_response.is_success:
        response_map = {response.id: response for response in batch_response if response.id is not None}

        for request in batch_request:
            if request.id is not None:
                response = response_map.pop(request.id, None)
                if response is None:
                    raise exceptions.IdentityError(f"response '{request.id}' not found")

        if response_map:
            raise exceptions.IdentityError(f"unexpected response found: {response_map.keys()}")
