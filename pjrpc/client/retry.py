import asyncio
import dataclasses as dc
import itertools as it
import logging
import time
from typing import Any, Awaitable, Callable, Generator, Iterator, Optional, Set, Type

from pjrpc.common import AbstractResponse

logger = logging.getLogger(__package__)

Jitter = Callable[[], float]


@dc.dataclass(frozen=True)
class Backoff:
    """
    JSON-RPC request retry strategy.

    :param attempts: retries number
    :param jitter: retry delay jitter generator
    """

    attempts: int
    jitter: Jitter = lambda: 0.0

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
            for _ in range(self.attempts):
                yield self.interval + self.jitter()

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
            for n, base in enumerate(it.repeat(self.base, self.attempts)):
                value = base * (self.factor ** n) + self.jitter()
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

            for _ in range(self.attempts):
                value = cur * self.multiplier + self.jitter()
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
    codes: Optional[Set[int]] = None
    exceptions: Optional[Set[Type[Exception]]] = None


def retry(
    func: Callable[..., AbstractResponse],
    retry_strategy: RetryStrategy,
) -> Callable[..., AbstractResponse]:
    """
    Synchronous function retry decorator.

    :param func: function to be retried
    :param retry_strategy: retry strategy to be applied
    :return: decorated function
    """

    def wrapped(*args: Any, **kwargs: Any) -> AbstractResponse:
        delays = retry_strategy.backoff()

        for attempt in it.count(start=1):
            try:
                response = func(*args, **kwargs)
                if response.is_error and retry_strategy.codes and response.get_error().code in retry_strategy.codes:
                    delay = next(delays, None)
                    if delay is not None:
                        logger.debug("retrying request: attempt=%d, code=%s", attempt, response.error)
                        time.sleep(delay)
                        continue

                return response

            except tuple(retry_strategy.exceptions or {}) as e:
                delay = next(delays, None)
                if delay is not None:
                    logger.debug("retrying request: attempt=%d, exception=%r", attempt, e)
                    time.sleep(delay)
                else:
                    raise e
        else:
            raise AssertionError("unreachable")

    return wrapped


def retry_async(
    func: Callable[..., Awaitable[AbstractResponse]],
    retry_strategy: RetryStrategy,
) -> Callable[..., Awaitable[AbstractResponse]]:
    """
    Asynchronous function retry decorator.

    :param func: function to be retried
    :param retry_strategy: retry strategy to be applied
    :return: decorated function
    """

    async def wrapped(*args: Any, **kwargs: Any) -> AbstractResponse:
        delays = retry_strategy.backoff()

        for attempt in it.count(start=1):
            try:
                response = await func(*args, **kwargs)
                if response.is_error and retry_strategy.codes and response.get_error().code in retry_strategy.codes:
                    delay = next(delays, None)
                    if delay is not None:
                        logger.debug("retrying request: attempt=%d, code=%s", attempt, response.error)
                        await asyncio.sleep(delay)
                        continue

                return response

            except tuple(retry_strategy.exceptions or {}) as e:
                delay = next(delays, None)
                if delay is not None:
                    logger.debug("retrying request: attempt=%d, exception=%r", attempt, e)
                    await asyncio.sleep(delay)
                else:
                    raise e
        else:
            raise AssertionError("unreachable")

    return wrapped
