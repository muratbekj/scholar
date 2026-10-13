"""Per-request client identity for data isolation in cloud mode (spec D5, D16).

X-Client-Id is a browser-generated UUID, not authentication.
TODO: replace it with real identities from Firebase Auth or IAP.
"""
import uuid
from contextvars import ContextVar
from typing import Optional

from fastapi import HTTPException, Request

from .config import get_settings

_client_id: ContextVar[Optional[str]] = ContextVar("client_id", default=None)
_request_id: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


class IsolationError(RuntimeError):
    """Cloud-mode data access without a bound client id (fail closed instead of sharing data)."""


def cloud_mode() -> bool:
    return get_settings().cloud_mode


def bind(client_id: Optional[str], request_id: Optional[str] = None) -> None:
    _client_id.set(client_id)
    _request_id.set(request_id or uuid.uuid4().hex)


def current_client_id() -> Optional[str]:
    return _client_id.get()


def current_request_id() -> Optional[str]:
    return _request_id.get()


def scope_client_id() -> Optional[str]:
    """The client id data must be scoped to: None in local mode (single user), required in cloud mode."""
    if not cloud_mode():
        return None
    client_id = _client_id.get()
    if client_id is None:
        raise IsolationError("No client id bound for a cloud-mode data access")
    return client_id


async def client_context(request: Request) -> None:
    """Router dependency. Must stay async: a sync dependency runs in a worker thread and its
    ContextVar changes would not reach the endpoint."""
    request_id = request.headers.get("X-Request-Id") or uuid.uuid4().hex
    if not cloud_mode():
        bind(None, request_id)
        return
    try:
        client_id = str(uuid.UUID(request.headers.get("X-Client-Id", "").strip()))
    except ValueError:
        raise HTTPException(status_code=400, detail="X-Client-Id header with a UUID is required")
    bind(client_id, request_id)
