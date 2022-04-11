# Module implementing the pretty printing log function pplog() for nice logs
import inspect
import os
import pprint
import rich.logging
import rich.traceback
from logging import basicConfig, Filter, getLogger, INFO, Logger, LogRecord
from pathlib import Path
from typing import Any


def get_terminal_width() -> int:
    columns = os.environ.get("COLUMNS")
    if columns:
        return int(columns)
    try:
        return os.get_terminal_size()[0]
    except OSError:
        return 110  # For AREPL(it does not emulate a tty terminal)


class UpStackedLogger:
    """Helper class for custom log functions to log the call site of them."""

    def __init__(self, logger: Logger, n: int) -> None:
        self.logger = logger

        calling_frame = inspect.stack()[n + 1].frame
        trace = inspect.getframeinfo(calling_frame)

        class UpStackFilter(Filter):
            def filter(self, record: LogRecord) -> bool:
                record.lineno = trace.lineno
                record.pathname = trace.filename
                record.filename = Path(trace.filename).name
                return True

        self.f = UpStackFilter()

    def __enter__(self) -> Logger:
        self.logger.addFilter(self.f)
        return self.logger

    def __exit__(self, *args: Any, **kwds: Any) -> None:
        self.logger.removeFilter(self.f)


def pplog(msg: Any, logger: Logger = getLogger(), **kwargs: Any) -> None:
    """pretty print log function which records its call site as log location"""
    with UpStackedLogger(logger, n=1) as logger:
        logger.info(pprint.pformat(msg, width=get_terminal_width(), **kwargs))


if __name__ == "__main__":
    """Demonstrates the pplog function showing the call site as log location"""
    obj = [{"wlp0s20f3": "Some info"}, {"enx0c3796090408": "More Information"}]
    basicConfig(
        level=INFO,
        format="%(message)s",
        handlers=[rich.logging.RichHandler(show_time=False, show_level=False)],
    )
    pplog(obj)
