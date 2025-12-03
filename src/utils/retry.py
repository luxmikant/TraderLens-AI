"""Retry & circuit-breaker utilities for fault tolerance."""
from __future__ import annotations

import asyncio
import functools
import logging
import random
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Awaitable, Callable, TypeVar, Generic, Optional, List

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class RetryConfig:
    """Configuration for retry behaviour."""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    exponential_base: float = 2.0
    jitter: bool = True
    retriable_exceptions: tuple = (Exception,)


def compute_delay(attempt: int, config: RetryConfig) -> float:
    """Calculate exponential backoff delay with optional jitter."""
    delay = min(config.base_delay * (config.exponential_base ** attempt), config.max_delay)
    if config.jitter:
        delay *= random.uniform(0.5, 1.5)
    return delay


async def retry_async(
    func: Callable[..., Awaitable[T]],
    *args,
    config: Optional[RetryConfig] = None,
    **kwargs
) -> T:
    """Execute an async function with retry/backoff."""
    cfg = config or RetryConfig()
    last_exc: Exception = Exception("No attempts made")
    for attempt in range(cfg.max_attempts):
        try:
            return await func(*args, **kwargs)
        except cfg.retriable_exceptions as exc:
            last_exc = exc
            if attempt == cfg.max_attempts - 1:
                logger.error("All %d attempts failed for %s: %s", cfg.max_attempts, func.__name__, exc)
                raise
            delay = compute_delay(attempt, cfg)
            logger.warning(
                "Attempt %d/%d for %s failed (%s). Retrying in %.2fs...",
                attempt + 1, cfg.max_attempts, func.__name__, exc, delay
            )
            await asyncio.sleep(delay)
    raise last_exc


def with_retry(config: Optional[RetryConfig] = None):
    """Decorator to add retry behaviour to an async function."""
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            return await retry_async(func, *args, config=config, **kwargs)
        return wrapper
    return decorator


# ========================== Circuit Breaker ==========================

@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    half_open_max_calls: int = 1


class CircuitBreakerOpen(Exception):
    """Raised when circuit is open and call is rejected."""


class CircuitBreaker(Generic[T]):
    """
    Simple circuit breaker implementation.
    
    States:
    - CLOSED: normal operation, calls pass through.
    - OPEN: failures exceeded threshold; calls rejected immediately.
    - HALF_OPEN: after recovery timeout, limited calls allowed to probe health.
    """
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

    def __init__(self, name: str, config: Optional[CircuitBreakerConfig] = None):
        self.name = name
        self.cfg = config or CircuitBreakerConfig()
        self._state = self.CLOSED
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._half_open_calls = 0

    @property
    def state(self) -> str:
        # Check if we should transition from OPEN -> HALF_OPEN
        if self._state == self.OPEN and self._last_failure_time:
            if time.time() - self._last_failure_time >= self.cfg.recovery_timeout:
                self._state = self.HALF_OPEN
                self._half_open_calls = 0
        return self._state

    def record_success(self):
        """Record successful call; reset failure counter if in HALF_OPEN."""
        if self._state == self.HALF_OPEN:
            self._state = self.CLOSED
            logger.info("CircuitBreaker[%s] recovered (CLOSED)", self.name)
        self._failure_count = 0

    def record_failure(self, exc: Exception):
        """Record failure; open circuit if threshold reached."""
        self._failure_count += 1
        self._last_failure_time = time.time()
        if self._failure_count >= self.cfg.failure_threshold:
            self._state = self.OPEN
            logger.warning("CircuitBreaker[%s] OPEN after %d failures", self.name, self._failure_count)

    async def call(self, func: Callable[..., Awaitable[T]], *args, **kwargs) -> T:
        """Execute function through circuit breaker."""
        state = self.state  # triggers potential OPEN->HALF_OPEN transition
        if state == self.OPEN:
            raise CircuitBreakerOpen(f"Circuit breaker '{self.name}' is open")
        if state == self.HALF_OPEN:
            if self._half_open_calls >= self.cfg.half_open_max_calls:
                raise CircuitBreakerOpen(f"Circuit breaker '{self.name}' half-open limit reached")
            self._half_open_calls += 1

        try:
            result = await func(*args, **kwargs)
            self.record_success()
            return result
        except Exception as exc:
            self.record_failure(exc)
            raise


# ========================== Health Check ==========================

@dataclass
class HealthStatus:
    name: str
    healthy: bool
    latency_ms: float
    message: str = ""
    checked_at: datetime = field(default_factory=datetime.utcnow)


class HealthChecker:
    """Aggregate health checks for multiple components."""

    def __init__(self):
        self._checks: dict[str, Callable[[], Awaitable[bool]]] = {}

    def register(self, name: str, check_fn: Callable[[], Awaitable[bool]]):
        self._checks[name] = check_fn

    async def run_all(self) -> List[HealthStatus]:
        results: List[HealthStatus] = []
        for name, fn in self._checks.items():
            start = time.perf_counter()
            try:
                ok = await fn()
                latency = (time.perf_counter() - start) * 1000
                results.append(HealthStatus(name=name, healthy=ok, latency_ms=latency))
            except Exception as e:
                latency = (time.perf_counter() - start) * 1000
                results.append(HealthStatus(name=name, healthy=False, latency_ms=latency, message=str(e)))
        return results

    async def is_healthy(self) -> bool:
        statuses = await self.run_all()
        return all(s.healthy for s in statuses)


# Global health checker instance
health_checker = HealthChecker()
