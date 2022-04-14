import logging
import os
import pprint_log
import rich
import rich.logging
from typing import Any


def setup_logfile() -> None:
    """Setup logfile logging according to environment variable."""
    if "CONNMAN_LOGFILE" in os.environ:
        logfile = os.environ["CONNMAN_LOGFILE"].strip()
        handler = logging.FileHandler(logfile, "w", "utf-8")
        handler.formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s @ "
            "%(filename)s:%(funcName)s:%(lineno)s] %(process)s - %(message)s"
        )
        logging.root.addHandler(handler)


def setup_loglevel(logger: logging.Logger) -> None:
    level = logging.INFO
    env_log_level = os.environ.get("CONNMAN_LOGLEVEL", None)
    if env_log_level is not None:
        lvl = getattr(logging, env_log_level.strip(), None)
        if isinstance(lvl, int):
            level = lvl
        else:
            logger.warning("Invalid CONNMAN_LOGLEVEL: %r", env_log_level)
        logger.setLevel(level)


def init_rich_logger(server: Any) -> None:
    console = rich.console.Console(width=pprint_log.get_terminal_width())
    server.logger.addHandler(
        rich.logging.RichHandler(
            show_time=False,
            show_level=False,
            keywords=["Greeting", "Hello", "MyExampleServer", "tick", "sum"],
            console=console,
        )
    )
    for handler in server.logger.handlers:
        if str(handler) == "<StreamHandler <stderr> (NOTSET)>":
            server.logger.removeHandler(handler)
    setup_loglevel(server.logger)
    setup_logfile()
