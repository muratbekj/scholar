"""Test isolation from the developer's shell and local data.

Runs before any test module imports the app (the service singletons read settings at import).
Strips every setting the app reads, so a shell configured for Vertex or custom CORS doesn't
change test results, and points storage at a throwaway directory instead of ./chroma_db and
./uploads.
"""
import atexit
import os
import shutil
import tempfile

# Settings read by app/core/config.py (OLLAMA_HOST is left alone: CI points it at a closed port).
_PREFIXES = ("VERTEX_", "GOOGLE_CLOUD_")
_NAMES = (
    "LLM_PROVIDER", "OLLAMA_LLM_MODEL", "OLLAMA_EMBED_MODEL", "GOOGLE_API_KEY", "GEMINI_API_KEY",
    "CORS_ORIGINS", "FRONTEND_URL", "CHROMA_DIR", "UPLOAD_DIR", "VECTOR_BACKEND", "DATABASE_URL", "STORAGE_BACKEND",
    "GCS_BUCKET", "SESSION_BACKEND", "MAX_UPLOAD_MB", "MAX_CHUNKS_PER_DOC", "RATE_LIMIT_PER_MIN",
    "GOOGLE_CREDENTIALS_JSON", "RATE_LIMIT_GLOBAL_PER_MIN", "MAX_TEXT_CHARS",
)

for _name in list(os.environ):
    if _name.startswith(_PREFIXES) or _name in _NAMES:
        del os.environ[_name]

_data_dir = tempfile.mkdtemp(prefix="scholar-tests-")
atexit.register(shutil.rmtree, _data_dir, ignore_errors=True)
os.environ["CHROMA_DIR"] = os.path.join(_data_dir, "chroma_db")
os.environ["UPLOAD_DIR"] = os.path.join(_data_dir, "uploads")

from app.core.config import get_settings  # noqa: E402

get_settings.cache_clear()


import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_request_context():
    """Tests bind client ids directly; don't let one leak into the next test."""
    yield
    from app.core import request_context

    request_context.bind(None, None)


@pytest.fixture
def cloud_app(monkeypatch, tmp_path):
    """The real app in cloud mode on throwaway local backends (no GCP, no Ollama, no LLM calls)."""
    from types import SimpleNamespace

    from fastapi.testclient import TestClient

    from app.api.routes import files as files_routes
    from app.core import guardrails, request_context
    from app.main import app
    from app.services import flashcard_service, qa_service, quiz_service, rag_pipeline
    from app.services.document import DocumentService
    from app.services.session_store import MemorySessionStore
    from app.services.storage import LocalStorage
    from app.services.vector_store import VectorStoreService
    from app.tests.fakes import KeywordEmbeddings

    monkeypatch.setattr(request_context, "cloud_mode", lambda: True)
    monkeypatch.setattr(guardrails, "rate_limiter", guardrails.SlidingWindowRateLimiter())
    documents = DocumentService(storage=LocalStorage(tmp_path / "uploads"))
    vectors = VectorStoreService(persist_directory=str(tmp_path / "chroma"), embeddings=KeywordEmbeddings())
    pipeline = rag_pipeline.rag_pipeline_service
    monkeypatch.setattr(pipeline, "document_service", documents)
    monkeypatch.setattr(pipeline, "vector_store_service", vectors)
    monkeypatch.setattr(files_routes, "document_service", documents)
    for service in (qa_service.qa_service, quiz_service.quiz_service, flashcard_service.flashcard_service):
        monkeypatch.setattr(service, "document_service", documents)
    # QA and quiz have heuristic fallbacks; flashcards need an LLM, so fake its one call
    monkeypatch.setattr(qa_service.qa_service, "use_llm", False)
    monkeypatch.setattr(quiz_service.quiz_service, "use_llm", False)

    async def fake_flashcards(content):
        return [{"id": "card-1", "front": "What do chloroplasts capture?", "back": "Light energy", "difficulty": "easy"}]

    monkeypatch.setattr(flashcard_service, "llm_service", SimpleNamespace(generate_flashcards=fake_flashcards))
    monkeypatch.setattr(qa_service.qa_service, "sessions", MemorySessionStore())
    monkeypatch.setattr(quiz_service.quiz_service, "sessions", MemorySessionStore())
    return SimpleNamespace(client=TestClient(app), documents=documents, vectors=vectors)
