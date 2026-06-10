"""
Retry decorator with exponential backoff for flaky operations.
"""

import asyncio
import functools
import logging
from typing import Callable, Type

logger = logging.getLogger("scraper")


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple[Type[Exception], ...] = (Exception,),
):
    """
    Retry decorator with exponential backoff.

    Args:
        max_attempts: Maximum number of attempts
        delay: Initial delay between retries (seconds)
        backoff: Multiplier for delay after each retry
        exceptions: Tuple of exception types to catch

    Usage:
        @retry(max_attempts=3, delay=1.0)
        async def flaky_function():
            ...
    """

    def decorator(func: Callable):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts:
                        logger.warning(
                            f"[retry] {func.__name__} attempt {attempt}/{max_attempts} "
                            f"failed: {e}. Retrying in {current_delay:.1f}s..."
                        )
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(
                            f"[retry] {func.__name__} failed after {max_attempts} attempts: {e}"
                        )

            raise last_exception

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            import time

            current_delay = delay
            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts:
                        logger.warning(
                            f"[retry] {func.__name__} attempt {attempt}/{max_attempts} "
                            f"failed: {e}. Retrying in {current_delay:.1f}s..."
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(
                            f"[retry] {func.__name__} failed after {max_attempts} attempts: {e}"
                        )

            raise last_exception

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator
