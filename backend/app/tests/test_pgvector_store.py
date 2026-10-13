import os
import uuid

import pytest

from app.core import request_context as rc
from app.tests import vector_store_contract as contract
from app.tests.fakes import KeywordEmbeddings

DB_URL = os.environ.get("TEST_DATABASE_URL")
pytestmark = [pytest.mark.postgres, pytest.mark.skipif(not DB_URL, reason="TEST_DATABASE_URL not set")]


@pytest.fixture
def store(monkeypatch):
    from app.services.vector_store import VectorStoreService

    monkeypatch.setattr(rc, "cloud_mode", lambda: True)
    return VectorStoreService(backend="pgvector", database_url=DB_URL,
                              collection_name=f"test_{uuid.uuid4().hex}", embeddings=KeywordEmbeddings())


async def test_cloud_mode_scopes_every_read_and_delete(store):
    await contract.check_cloud_mode_scopes_every_read_and_delete(store)


async def test_unbound_cloud_access_returns_nothing(store):
    await contract.check_unbound_cloud_access_returns_nothing(store)


async def test_relevance_is_unit_range_and_ordered(store):
    await contract.check_relevance_is_unit_range_and_ordered(store)
