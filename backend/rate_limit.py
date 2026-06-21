"""Minimal in-memory rate limiting for public API endpoints."""
from __future__ import annotations

import os
import threading
import time
from collections import deque
from typing import Deque

_lock = threading.Lock()
_buckets: dict[str, Deque[float]] = {}


def _limit(env_name: str, default: int) -> int:
    try:
        return max(1, int(os.getenv(env_name, str(default))))
    except ValueError:
        return default


def _window_seconds() -> int:
    try:
        return max(30, int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "3600")))
    except ValueError:
        return 3600


def allow(key: str, *, max_events: int) -> bool:
    """Return True if the event is allowed under the sliding window limit."""
    now = time.monotonic()
    window = _window_seconds()
    bucket_key = f"{key}|{max_events}|{window}"
    with _lock:
        bucket = _buckets.setdefault(bucket_key, deque())
        while bucket and (now - bucket[0]) > window:
            bucket.popleft()
        if len(bucket) >= max_events:
            return False
        bucket.append(now)
        return True


def allow_report_upload(client_key: str) -> bool:
    return allow(
        f"reports:{client_key}",
        max_events=_limit("RATE_LIMIT_REPORTS_PER_HOUR", 40),
    )


def allow_pin_creation(client_key: str) -> bool:
    return allow(
        f"sessions:{client_key}",
        max_events=_limit("RATE_LIMIT_PIN_CREATE_PER_HOUR", 30),
    )
