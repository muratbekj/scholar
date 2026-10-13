"""Isolation and scoring checks shared by the Chroma and pgvector backends."""
import uuid

from app.core import request_context as rc
from app.tests.fakes import chunk

A, B = str(uuid.uuid4()), str(uuid.uuid4())


async def ingest(store, client_id, file_id, text):
    rc.bind(client_id)
    result = await store.add_document_chunks(file_id, [chunk(f"{file_id}-c0", text)])
    assert result["success"], result
    return result


async def check_cloud_mode_scopes_every_read_and_delete(store):
    await ingest(store, A, "fa", "chloroplast light stroma")
    await ingest(store, B, "fb", "mitochondria glucose oxygen")

    rc.bind(A)
    assert [r["metadata"]["file_id"] for r in await store.search_similar("light glucose", k=5)] == ["fa"]
    assert await store.search_by_file_id("fb") == []
    assert await store.search_by_file_id("fb", query="glucose") == []
    stats = await store.get_collection_stats()
    assert (stats["total_documents"], stats["unique_files"]) == (1, 1)
    await store.delete_file_documents("fb")  # A deleting B's file must be a no-op

    rc.bind(B)
    remaining = await store.search_by_file_id("fb")
    assert len(remaining) == 1 and remaining[0]["metadata"]["client_id"] == B
    assert all(r["metadata"]["client_id"] == B for r in await store.search_similar("glucose", k=5))


async def check_unbound_cloud_access_returns_nothing(store):
    await ingest(store, A, "fa", "chloroplast light")
    rc.bind(None)
    assert await store.search_similar("light", k=5) == []
    assert (await store.add_document_chunks("fx", [chunk("fx-c0", "light")]))["success"] is False


async def check_relevance_is_unit_range_and_ordered(store):
    rc.bind(A)
    await store.add_document_chunks("f", [chunk("near", "chloroplast light light"), chunk("far", "mitochondria glucose")])
    results = {r["id"]: r["similarity_score"] for r in await store.search_similar("light chloroplast", k=2)}
    assert all(0.0 <= s <= 1.0 for s in results.values())
    assert results["near"] > results["far"]
