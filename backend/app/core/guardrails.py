"""Cost guardrails for cloud mode (spec D13): upload size, chunks per document, per-client rate limit.

Local mode is unaffected. The rate limit is in memory, per Cloud Run instance.
"""
import math
import threading
import time
from collections import defaultdict, deque
from typing import Callable, Deque, Dict, Optional

from fastapi import HTTPException

from . import request_context
from .config import get_settings


class DocumentTooLargeError(Exception):
    """A document would split into more chunks than MAX_CHUNKS_PER_DOC (mapped to HTTP 413)."""


def enforce_upload_size(num_bytes: int) -> None:
    if not request_context.cloud_mode():
        return
    limit_mb = get_settings().max_upload_mb
    if num_bytes > limit_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File exceeds the {limit_mb} MB upload limit")


def check_chunk_count(num_chunks: int) -> None:
    if not request_context.cloud_mode():
        return
    limit = get_settings().max_chunks_per_doc
    if num_chunks > limit:
        raise DocumentTooLargeError(f"Document splits into {num_chunks} chunks; the limit is {limit}")


class SlidingWindowRateLimiter:
    def __init__(self, window_seconds: float = 60.0, clock: Callable[[], float] = time.monotonic):
        self.window_seconds = window_seconds
        self.clock = clock
        self._hits: Dict[str, Deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def hit(self, key: str, limit: int) -> Optional[float]:
        """Record a call; returns None if allowed, else the seconds until the next call is allowed."""
        now = self.clock()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] >= self.window_seconds:
                hits.popleft()
            if len(hits) >= limit:
                return self.window_seconds - (now - hits[0])
            hits.append(now)
            return None


rate_limiter = SlidingWindowRateLimiter()


def enforce_rate_limit() -> None:
    if not request_context.cloud_mode():
        return
    retry_after = rate_limiter.hit(request_context.scope_client_id(), get_settings().rate_limit_per_min)
    if retry_after is not None:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded; try again shortly",
            headers={"Retry-After": str(max(1, math.ceil(retry_after)))},
        )


async def rate_limited() -> None:
    """Route dependency for endpoints that call the LLM or the embedding model."""
    enforce_rate_limit()
