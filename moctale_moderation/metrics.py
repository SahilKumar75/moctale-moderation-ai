"""Prometheus metrics instrumentation."""
from __future__ import annotations

import time
from collections.abc import Callable
from functools import wraps
from typing import Any

from prometheus_client import Counter, Histogram

# Metrics
MODERATION_REQUESTS_TOTAL = Counter(
    "moctale_moderation_requests_total",
    "Total number of moderation requests processed",
)

MODERATION_DECISIONS_TOTAL = Counter(
    "moctale_moderation_decisions_total",
    "Total number of moderation decisions by action",
    ["action", "category"],
)

MODERATION_LATENCY_SECONDS = Histogram(
    "moctale_moderation_latency_seconds",
    "Latency of moderation requests in seconds",
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

MODERATION_ERRORS_TOTAL = Counter(
    "moctale_moderation_errors_total",
    "Total number of errors during moderation processing",
    ["error_type"],
)


def track_latency() -> Callable:
    """Decorator to track function latency and request counts."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            MODERATION_REQUESTS_TOTAL.inc()
            start_time = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                MODERATION_LATENCY_SECONDS.observe(time.perf_counter() - start_time)
                return result
            except Exception as e:
                MODERATION_ERRORS_TOTAL.labels(error_type=type(e).__name__).inc()
                raise

        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            MODERATION_REQUESTS_TOTAL.inc()
            start_time = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                MODERATION_LATENCY_SECONDS.observe(time.perf_counter() - start_time)
                return result
            except Exception as e:
                MODERATION_ERRORS_TOTAL.labels(error_type=type(e).__name__).inc()
                raise

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator
