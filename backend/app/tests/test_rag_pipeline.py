from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from app.services.rag_pipeline import RAGPipelineService


def make_pipeline(store_result):
    upload = SimpleNamespace(
        file_id="f1",
        size=11,
        upload_time=datetime(2026, 1, 1),
        content_summary={"full_text": "hello world", "chunking_info": {"is_chunked": False}},
    )
    document_service = Mock()
    document_service.process_upload = AsyncMock(return_value=upload)
    embedding_service = Mock()
    embedding_service.embed_batch = AsyncMock(return_value=[])
    vector_store = Mock()
    vector_store.add_document_chunks = AsyncMock(return_value=store_result)
    pipeline = RAGPipelineService(document_service, embedding_service, vector_store)
    return pipeline, embedding_service, vector_store


async def test_chunks_are_embedded_once_by_the_vector_store_only():
    pipeline, embedding_service, vector_store = make_pipeline({"success": True, "documents_added": 1, "ids": ["f1_x"]})
    result = await pipeline.process_document_upload(b"hello world", "a.txt", enable_embedding=True)
    assert embedding_service.embed_batch.await_count == 0
    assert vector_store.add_document_chunks.await_count == 1
    assert result["embedding"] == {
        "enabled": True, "success": True,
        "total_embeddings": 1, "successful_embeddings": 1, "failed_embeddings": 0,
    }
    assert result["vector_storage"] == {"success": True, "documents_stored": 1}


async def test_store_failure_reports_failed_embeddings_like_before():
    pipeline, _, _ = make_pipeline({"success": False, "error": "ollama down"})
    result = await pipeline.process_document_upload(b"hello world", "a.txt", enable_embedding=True)
    assert result["status"] == "completed"
    assert result["embedding"] == {
        "enabled": True, "success": True,
        "total_embeddings": 1, "successful_embeddings": 0, "failed_embeddings": 1,
    }
    assert result["vector_storage"] == {"success": False, "documents_stored": 0}


async def test_embedding_disabled_skips_vector_store():
    pipeline, embedding_service, vector_store = make_pipeline({"success": True, "documents_added": 1})
    result = await pipeline.process_document_upload(b"hello world", "a.txt", enable_embedding=False)
    assert vector_store.add_document_chunks.await_count == 0
    assert embedding_service.embed_batch.await_count == 0
    assert result["embedding"] == {
        "enabled": False, "success": False,
        "total_embeddings": 0, "successful_embeddings": 0, "failed_embeddings": 0,
    }
    assert result["vector_storage"] == {"success": False, "documents_stored": 0}
