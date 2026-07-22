"""Exponential Backoff Reconnector for Outbound-Only gRPC Transport."""

from __future__ import annotations

import asyncio
import logging
import random
from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ExponentialBackoffReconnector:
    """Manages outbound reconnection attempts using exponential backoff with full jitter

    for network resilience in standalone bank client daemons.
    """

    def __init__(
        self,
        max_retries: int = 10,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_factor: float = 2.0,
    ) -> None:
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.current_attempt = 0

    def compute_next_delay(self) -> float:
        """Calculates exponential backoff delay with random jitter."""
        calculated = self.initial_delay * (self.backoff_factor**self.current_attempt)
        capped = min(calculated, self.max_delay)
        # Full jitter between 0.5x and 1.0x capped delay
        jittered = capped * random.uniform(0.5, 1.0)
        return jittered

    def reset(self) -> None:
        """Resets retry attempt counter upon successful connection."""
        self.current_attempt = 0

    async def execute_with_retry(
        self,
        action: Callable[[], Awaitable[T]],
        on_error_callback: Callable[[Exception, int, float], None] | None = None,
    ) -> T:
        """Executes an async action with exponential backoff retries."""
        while True:
            try:
                result = await action()
                self.reset()
                return result
            except Exception as exc:
                self.current_attempt += 1
                if self.current_attempt > self.max_retries:
                    logger.error(
                        "Max reconnection retries reached (%d/%d). Aborting operation: %s",
                        self.current_attempt - 1,
                        self.max_retries,
                        exc,
                    )
                    raise exc

                delay = self.compute_next_delay()
                logger.warning(
                    "Connection error (Attempt %d/%d): %s. Retrying in %.2fs...",
                    self.current_attempt,
                    self.max_retries,
                    exc,
                    delay,
                )

                if on_error_callback:
                    on_error_callback(exc, self.current_attempt, delay)

                await asyncio.sleep(delay)
