"""Structured logging configuration for Moctale Moderation AI."""
from __future__ import annotations

import logging
import os
import sys
from typing import Literal


def configure_logging(
    level: str | None = None,
    fmt: Literal["json", "text"] | None = None,
) -> None:
    """Configure root logger for structured output.

    Args:
        level: Log level string (DEBUG/INFO/WARNING/ERROR). Defaults to LOG_LEVEL env var or INFO.
        fmt: Output format. Defaults to LOG_FORMAT env var or 'json' in production.
    """
    level = level or os.getenv("LOG_LEVEL", "INFO")
    fmt = fmt or os.getenv("LOG_FORMAT", "json")  # type: ignore[assignment]

    numeric_level = getattr(logging, level.upper(), logging.INFO)

    handler: logging.StreamHandler

    if fmt == "json":
        try:
            from pythonjsonlogger import jsonlogger  # type: ignore[import]

            handler = logging.StreamHandler(sys.stdout)
            formatter = jsonlogger.JsonFormatter(
                "%(asctime)s %(name)s %(levelname)s %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S",
            )
            handler.setFormatter(formatter)
        except ImportError:
            handler = logging.StreamHandler(sys.stdout)
            fmt = "text"

    if fmt != "json":
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
        handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(numeric_level)

    # Silence noisy third-party loggers
    for name in ("httpx", "httpcore", "uvicorn.access"):
        logging.getLogger(name).setLevel(logging.WARNING)
