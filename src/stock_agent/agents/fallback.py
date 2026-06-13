from __future__ import annotations

from time import monotonic

import psycopg

from stock_agent.config import get_settings


_FALLBACK_ERROR_MARKERS = (
    "api",
    "authentication",
    "connection",
    "connectionerror",
    "database",
    "db",
    "interfaceerror",
    "operationalerror",
    "psycopg",
    "rate limit",
    "timeout",
)

_DB_FAILURE_CACHE_SECONDS = 30
_db_failure: tuple[float, str] | None = None


def should_fallback(exc: Exception) -> bool:
    """Return True for expected external dependency failures."""
    if isinstance(exc, (ConnectionError, OSError, TimeoutError)):
        return True
    error_text = f"{exc.__class__.__name__}: {exc}".lower()
    return any(marker in error_text for marker in _FALLBACK_ERROR_MARKERS)


def fallback_reason(exc: Exception) -> str:
    return f"{exc.__class__.__name__}: {exc}"


def ensure_database_available(connect_timeout: int = 1) -> None:
    """Fast DB health check with a short-lived failure cache."""
    global _db_failure

    now = monotonic()
    if _db_failure is not None:
        failed_at, reason = _db_failure
        if now - failed_at < _DB_FAILURE_CACHE_SECONDS:
            raise ConnectionError(reason)
        _db_failure = None

    try:
        with psycopg.connect(
            get_settings().resolved_database_url,
            connect_timeout=connect_timeout,
        ):
            return
    except Exception as exc:
        reason = fallback_reason(exc)
        _db_failure = (now, reason)
        raise ConnectionError(reason) from exc
