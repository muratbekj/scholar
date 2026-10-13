import asyncio
import uuid
from pathlib import Path

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.core import request_context as rc

A = str(uuid.uuid4())


def make_app() -> FastAPI:
    app = FastAPI()

    @app.get("/who", dependencies=[Depends(rc.client_context)])
    async def who():
        return {
            "client_id": rc.current_client_id(),
            "request_id": rc.current_request_id(),
            "thread_client_id": await asyncio.to_thread(rc.current_client_id),
        }

    return app


def test_cloud_mode_requires_a_uuid_header(monkeypatch):
    monkeypatch.setattr(rc, "cloud_mode", lambda: True)
    client = TestClient(make_app())
    assert client.get("/who").status_code == 400
    assert client.get("/who", headers={"X-Client-Id": "not-a-uuid"}).status_code == 400


def test_cloud_mode_binds_normalized_client_id_visible_in_worker_threads(monkeypatch):
    monkeypatch.setattr(rc, "cloud_mode", lambda: True)
    body = TestClient(make_app()).get("/who", headers={"X-Client-Id": A.upper()}).json()
    assert body["client_id"] == A
    assert body["thread_client_id"] == A
    assert body["request_id"]


def test_local_mode_ignores_the_header(monkeypatch):
    monkeypatch.setattr(rc, "cloud_mode", lambda: False)
    body = TestClient(make_app()).get("/who", headers={"X-Client-Id": A}).json()
    assert body["client_id"] is None
    assert body["request_id"]


def test_scope_is_none_in_local_mode_even_when_bound(monkeypatch):
    monkeypatch.setattr(rc, "cloud_mode", lambda: False)
    rc.bind(A)
    assert rc.scope_client_id() is None


def test_scope_fails_closed_in_cloud_mode_without_a_client(monkeypatch):
    monkeypatch.setattr(rc, "cloud_mode", lambda: True)
    rc.bind(None)
    with pytest.raises(rc.IsolationError):
        rc.scope_client_id()


async def test_scope_reaches_code_running_in_asyncio_to_thread(monkeypatch):
    monkeypatch.setattr(rc, "cloud_mode", lambda: True)
    rc.bind(A)
    assert await asyncio.to_thread(rc.scope_client_id) == A


def test_app_routers_require_client_in_cloud_mode_but_health_stays_open(monkeypatch):
    from app.main import app

    monkeypatch.setattr(rc, "cloud_mode", lambda: True)
    client = TestClient(app)
    assert client.get("/health").status_code == 200
    assert client.get("/files/formats").status_code == 400
    assert client.get("/files/formats", headers={"X-Client-Id": A}).status_code == 200


def test_no_run_in_executor_in_app_code():
    # loop.run_in_executor does not copy ContextVars into the worker thread (spec D8)
    root = Path(__file__).resolve().parents[1]
    offenders = [str(p) for p in root.rglob("*.py") if "tests" not in p.parts and "run_in_executor" in p.read_text()]
    assert offenders == []
