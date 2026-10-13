import uuid

import pytest

from app.core import guardrails, request_context
from app.core.config import Settings
from app.core.guardrails import (
    SlidingWindowRateLimiter,
    check_chunk_count,
    enforce_rate_limit,
    enforce_upload_size,
)

A, B = str(uuid.uuid4()), str(uuid.uuid4())


@pytest.fixture
def small_limits(monkeypatch):
    limits = Settings.from_env({"MAX_UPLOAD_MB": "1", "RATE_LIMIT_PER_MIN": "2", "MAX_CHUNKS_PER_DOC": "2"})
    monkeypatch.setattr(guardrails, "get_settings", lambda: limits)


def test_sliding_window_allows_the_limit_then_blocks_until_the_window_passes():
    now = [0.0]
    limiter = SlidingWindowRateLimiter(window_seconds=60, clock=lambda: now[0])
    assert limiter.hit("a", 2) is None
    assert limiter.hit("a", 2) is None
    assert limiter.hit("a", 2) == pytest.approx(60)
    assert limiter.hit("b", 2) is None  # limits are per key
    now[0] = 60.0
    assert limiter.hit("a", 2) is None


def test_upload_over_the_size_limit_is_413(cloud_app, small_limits):
    response = cloud_app.client.post("/files/upload", params={"study_mode": "quiz"},
                                     files={"file": ("big.txt", b"a" * (1024 * 1024 + 1), "text/plain")},
                                     headers={"X-Client-Id": A})
    assert response.status_code == 413


async def test_document_over_the_chunk_limit_is_413_and_not_stored(cloud_app, small_limits):
    big = ("Sentence about chloroplasts and light. " * 400).encode()
    response = cloud_app.client.post("/files/upload", params={"study_mode": "qa"},
                                     files={"file": ("big.txt", big, "text/plain")}, headers={"X-Client-Id": A})
    assert response.status_code == 413
    assert await cloud_app.documents.storage.list_prefix("") == []


def test_llm_routes_are_rate_limited_per_client(cloud_app, small_limits):
    def ask(client_id):
        return cloud_app.client.post("/qa/ask", json={"question": "What is light?", "file_id": "f", "filename": "n"},
                                     headers={"X-Client-Id": client_id})

    assert ask(A).status_code == 200
    assert ask(A).status_code == 200
    blocked = ask(A)
    assert blocked.status_code == 429
    assert int(blocked.headers["Retry-After"]) >= 1
    assert ask(B).status_code == 200


def test_local_mode_has_no_limits(monkeypatch, small_limits):
    monkeypatch.setattr(request_context, "cloud_mode", lambda: False)
    enforce_upload_size(50 * 1024 * 1024)
    check_chunk_count(10_000)
    for _ in range(5):
        enforce_rate_limit()


# --- review fixes: rotating client ids, unpunctuated text, limiter memory ------------

@pytest.fixture
def tight_limits(monkeypatch):
    limits = Settings.from_env({"RATE_LIMIT_PER_MIN": "100", "RATE_LIMIT_GLOBAL_PER_MIN": "3",
                                "MAX_TEXT_CHARS": "1000"})
    monkeypatch.setattr(guardrails, "get_settings", lambda: limits)


def test_rotating_client_ids_still_hit_the_instance_wide_limit(cloud_app, tight_limits):
    statuses = [
        cloud_app.client.post("/qa/ask", json={"question": "q", "file_id": "f", "filename": "n"},
                              headers={"X-Client-Id": str(uuid.uuid4())}).status_code
        for _ in range(4)
    ]
    assert statuses == [200, 200, 200, 429]


async def test_unpunctuated_text_over_the_text_limit_is_413_and_not_stored(cloud_app, tight_limits):
    text = ("lorem ipsum dolor sit amet " * 100).encode()  # one sentence-chunk, 2700 chars
    response = cloud_app.client.post("/files/upload", params={"study_mode": "quiz"},
                                     files={"file": ("wall.txt", text, "text/plain")}, headers={"X-Client-Id": A})
    assert response.status_code == 413
    assert await cloud_app.documents.storage.list_prefix("") == []


def test_limiter_forgets_idle_clients():
    now = [0.0]
    limiter = SlidingWindowRateLimiter(window_seconds=60, clock=lambda: now[0])
    for i in range(1000):
        limiter.hit(f"client-{i}", 5)
    now[0] = 61.0
    limiter.hit("fresh", 5)
    assert limiter.tracked_keys() == 1


def test_text_limits_parsed_and_validated():
    assert Settings.from_env({}).max_text_chars == 500_000
    assert Settings.from_env({}).rate_limit_global_per_min == 100
    with pytest.raises(Exception, match="MAX_TEXT_CHARS"):
        Settings.from_env({"MAX_TEXT_CHARS": "0"})
