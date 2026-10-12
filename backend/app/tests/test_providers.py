import subprocess
import sys
import types

import pytest

from app.core.config import Settings
from app.core.providers import get_embeddings, get_llm

VERTEX = Settings.from_env({
    "LLM_PROVIDER": "vertex",
    "VERTEX_LLM_MODEL": "gemini-test-flash",
    "VERTEX_EMBED_MODEL": "gemini-embedding-001",
    "GOOGLE_CLOUD_PROJECT": "demo-project",
    "GOOGLE_CLOUD_LOCATION": "europe-west4",
})


@pytest.fixture
def fake_genai(monkeypatch):
    """Stand-in for langchain_google_genai that records constructor kwargs (no network, no install)."""
    created = []

    class _Recorder:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            created.append(self)

    module = types.ModuleType("langchain_google_genai")
    module.ChatGoogleGenerativeAI = type("ChatGoogleGenerativeAI", (_Recorder,), {})
    module.GoogleGenerativeAIEmbeddings = type("GoogleGenerativeAIEmbeddings", (_Recorder,), {})
    monkeypatch.setitem(sys.modules, "langchain_google_genai", module)
    return created


def test_ollama_llm_by_default():
    llm = get_llm(0.3, settings=Settings.from_env({}))
    assert type(llm).__name__ == "OllamaLLM"
    assert llm.model == "gpt-oss:20b"
    assert llm.temperature == 0.3


def test_ollama_llm_model_override():
    assert get_llm(0.7, model="llama3:8b", settings=Settings.from_env({})).model == "llama3:8b"


def test_ollama_embeddings_by_default():
    emb = get_embeddings(settings=Settings.from_env({}))
    assert type(emb).__name__ == "OllamaEmbeddings"
    assert emb.model == "nomic-embed-text"


def test_vertex_llm_uses_vertex_backend_with_project_and_location(fake_genai):
    llm = get_llm(0.2, settings=VERTEX)
    assert type(llm).__name__ == "ChatGoogleGenerativeAI"
    assert llm.kwargs == {
        "model": "gemini-test-flash",
        "project": "demo-project",
        "location": "europe-west4",
        "vertexai": True,
        "temperature": 0.2,
    }


def test_vertex_llm_never_receives_api_key_or_max_tokens(fake_genai):
    llm = get_llm(0.7, settings=VERTEX)
    assert "google_api_key" not in llm.kwargs
    assert "max_output_tokens" not in llm.kwargs


def test_vertex_thinking_budget_passed_only_when_set(fake_genai):
    with_budget = Settings.from_env({**{
        "LLM_PROVIDER": "vertex", "VERTEX_LLM_MODEL": "m", "VERTEX_EMBED_MODEL": "e",
        "GOOGLE_CLOUD_PROJECT": "p"}, "VERTEX_THINKING_BUDGET": "256"})
    assert get_llm(0.7, settings=with_budget).kwargs["thinking_budget"] == 256
    assert "thinking_budget" not in get_llm(0.7, settings=VERTEX).kwargs


def test_vertex_embeddings_use_vertex_backend(fake_genai):
    emb = get_embeddings(settings=VERTEX)
    assert type(emb).__name__ == "GoogleGenerativeAIEmbeddings"
    assert emb.kwargs == {
        "model": "gemini-embedding-001",
        "project": "demo-project",
        "location": "europe-west4",
        "vertexai": True,
    }


def test_importing_providers_does_not_import_google_packages():
    code = "import sys, app.core.providers; print('langchain_google_genai' in sys.modules)"
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert out.stdout.strip() == "False"
