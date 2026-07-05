"""
core/logger.py — Centralised logging factory for Hilda.
Writes coloured output to stdout and a rotating file at logs/hilda.log.
"""
import logging
import sys
from logging.handlers import RotatingFileHandler


import colorlog

from config.settings import settings

# Ensure logs directory exists
settings.LOGS_DIR.mkdir(parents=True, exist_ok=True)

_FORMATTER_CONSOLE = colorlog.ColoredFormatter(
    "%(log_color)s%(asctime)s [%(name)s] %(levelname)s%(reset)s — %(message)s",
    datefmt="%H:%M:%S",
    log_colors={
        "DEBUG": "cyan",
        "INFO": "green",
        "WARNING": "yellow",
        "ERROR": "red",
        "CRITICAL": "bold_red",
    },
)

_FORMATTER_FILE = logging.Formatter(
    "%(asctime)s [%(name)s] %(levelname)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# One rotating file handler shared across all loggers
_file_handler = RotatingFileHandler(
    settings.LOGS_DIR / "hilda.log",
    maxBytes=5 * 1024 * 1024,  # 5 MB
    backupCount=3,
    encoding="utf-8",
)
_file_handler.setFormatter(_FORMATTER_FILE)
_file_handler.setLevel(logging.DEBUG)

_console_handler = colorlog.StreamHandler(sys.stdout)
_console_handler.setFormatter(_FORMATTER_CONSOLE)
_console_handler.setLevel(logging.INFO)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger with both console and file handlers attached."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.addHandler(_console_handler)
        logger.addHandler(_file_handler)
        logger.setLevel(logging.DEBUG)
        logger.propagate = False
    return logger
