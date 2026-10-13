import pytest

from app.core import request_context as rc
from app.services.vector_store import VectorStoreService
from app.tests import vector_store_contract as contract
from app.tests.fakes import KeywordEmbeddings


@pytest.fixture
def store(tmp_path):
    return VectorStoreService(persist_directory=str(tmp_path / "chroma"), embeddings=KeywordEmbeddings())


@pytest.fixture
def cloud(monkeypatch):
    monkeypatch.setattr(rc, "cloud_mode", lambda: True)


async def test_cloud_mode_scopes_every_read_and_delete(store, cloud):
    await contract.check_cloud_mode_scopes_every_read_and_delete(store)


async def test_unbound_cloud_access_returns_nothing(store, cloud):
    await contract.check_unbound_cloud_access_returns_nothing(store)


async def test_relevance_is_unit_range_and_ordered(store, cloud):
    await contract.check_relevance_is_unit_range_and_ordered(store)


async def test_local_mode_is_unscoped(store, monkeypatch):
    monkeypatch.setattr(rc, "cloud_mode", lambda: False)
    await contract.ingest(store, None, "fa", "chloroplast light")
    results = await store.search_by_file_id("fa")
    assert len(results) == 1 and "client_id" not in results[0]["metadata"]
    assert (await store.get_collection_stats())["total_documents"] == 1
