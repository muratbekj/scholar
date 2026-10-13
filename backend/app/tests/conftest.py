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
    "CORS_ORIGINS", "CHROMA_DIR", "UPLOAD_DIR", "VECTOR_BACKEND", "DATABASE_URL", "STORAGE_BACKEND",
    "GCS_BUCKET", "SESSION_BACKEND", "MAX_UPLOAD_MB", "MAX_CHUNKS_PER_DOC", "RATE_LIMIT_PER_MIN",
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
