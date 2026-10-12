import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def preflight(origin: str):
    return client.options("/health", headers={"Origin": origin, "Access-Control-Request-Method": "GET"})


@pytest.mark.parametrize("origin", [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",  # packaged Electron app
    "null",                   # Electron file:// requests
])
def test_default_origins_allowed(origin):
    assert preflight(origin).headers.get("access-control-allow-origin") == origin


def test_unlisted_origin_not_allowed():
    assert "access-control-allow-origin" not in preflight("https://evil.example").headers
