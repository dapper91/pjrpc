import asyncio
import dataclasses as dc
import itertools as it
import logging
import time
from typing import Any, Callable, Generator, Iterator, Mapping, Optional

from pjrpc.client import AsyncMiddlewareHandler, MiddlewareHandler
from pjrpc.common import AbstractRequest, AbstractResponse

logger = logging.getLogger(__package__)

Jitter = Callable[[int], float]


@dc.dataclass(frozen=True)
class Backoff:
    """
    JSON-RPC request retry strategy.

    :param attempts: retries number
    :param jitter: retry delay jitter generator
    """

    attempts: int
    jitter: Jitter = lambda attempt: 0.0

    def __call__(self) -> Iterator[float]:
        """
        Returns delay iterator.
        """

        raise NotImplementedError


@dc.dataclass(frozen=True)
class PeriodicBackoff(Backoff):
    """
    Periodic request retry strategy.

    :param interval: retry delay
    """

    interval: float = 1.0

    def __call__(self) -> Iterator[float]:
        def gen() -> Generator[float, None, None]:
            for attempt in range(self.attempts):
                yield self.interval + self.jitter(attempt)

        return gen()


@dc.dataclass(frozen=True)
class ExponentialBackoff(Backoff):
    """
    Exponential request retry strategy.

    :param base: exponentially growing delay base
    :param factor: exponentially growing delay factor (multiplier)
    :param max_value: delay max value
    """

    base: float = 1.0
    factor: float = 2.0
    max_value: Optional[float] = None

    def __call__(self) -> Iterator[float]:
        def gen() -> Generator[float, None, None]:
            for attempt, base in enumerate(it.repeat(self.base, self.attempts)):
                value = base * (self.factor ** attempt) + self.jitter(attempt)
                yield min(self.max_value, value) if self.max_value is not None else value

        return gen()


@dc.dataclass(frozen=True)
class FibonacciBackoff(Backoff):
    """
    Fibonacci request retry strategy.

    :param multiplier: fibonacci interval sequence multiplier
    :param max_value: delay max value
    """

    multiplier: float = 1.0
    max_value: float = 1.0

    def __call__(self) -> Iterator[float]:
        def gen() -> Generator[float, None, None]:
            prev, cur = 1, 1

            for attempt in range(self.attempts):
                value = cur * self.multiplier + self.jitter(attempt)
                yield min(self.max_value, value) if self.max_value is not None else value

                tmp = cur
                cur = prev + cur
                prev = tmp

        return gen()


@dc.dataclass(frozen=True)
class RetryStrategy:
    """
    JSON-RPC request retry strategy.

    :param backoff: backoff delay generator
    :param codes: JSON-RPC response codes receiving which the request will be retried
    :param exceptions: exceptions catching which the request will be retried
    """

    backoff: Backoff
    codes: Optional[set[int]] = None
    exceptions: Optional[set[type[Exception]]] = None


class RetryMiddleware:
    def __init__(self, retry_strategy: RetryStrategy):
        self._retry_strategy = retry_strategy

    def __call__(
        self,
        request: AbstractRequest,
        request_kwargs: Mapping[str, Any],
        /,
        handler: MiddlewareHandler,
    ) -> Optional[AbstractResponse]:
        """
        Request retrying middleware
        """

        delays = self._retry_strategy.backoff()

        for attempt in it.count(start=1):
            try:
                response = handler(request, request_kwargs)
                if response is not None and response.is_error and self._retry_strategy.codes:
                    if (code := response.unwrap_error().code) in self._retry_strategy.codes:
                        delay = next(delays, None)
                        if delay is not None:
                            logger.debug("retrying request: attempt=%d, code=%s", attempt, code)
                            time.sleep(delay)
                            continue

                return response

            except tuple(self._retry_strategy.exceptions or {}) as e:
                delay = next(delays, None)
                if delay is not None:
                    logger.debug("retrying request: attempt=%d, exception=%r", attempt, e)
                    time.sleep(delay)
                else:
                    raise e
        else:
            raise AssertionError("unreachable")


class AsyncRetryMiddleware:
    def __init__(self, retry_strategy: RetryStrategy):
        self._retry_strategy = retry_strategy

    async def __call__(
        self,
        request: AbstractRequest,
        request_kwargs: Mapping[str, Any],
        /,
        handler: AsyncMiddlewareHandler,
    ) -> Optional[AbstractResponse]:
        """
        Asynchronous request retrying middleware
        """

        delays = self._retry_strategy.backoff()

        for attempt in it.count(start=1):
            try:
                response = await handler(request, request_kwargs)
                if response is not None and response.is_error and self._retry_strategy.codes:
                    if (code := response.unwrap_error().code) in self._retry_strategy.codes:
                        delay = next(delays, None)
                        if delay is not None:
                            logger.debug("retrying request: attempt=%d, code=%s", attempt, code)
                            await asyncio.sleep(delay)
                            continue

                return response

            except tuple(self._retry_strategy.exceptions or {}) as e:
                delay = next(delays, None)
                if delay is not None:
                    logger.debug("retrying request: attempt=%d, exception=%r", attempt, e)
                    await asyncio.sleep(delay)
                else:
                    raise e
        else:
            raise AssertionError("unreachable")
