# M2a Config, Providers, Wiring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let `LLM_PROVIDER=vertex` run Q&A, quiz and flashcards on Gemini via Vertex AI (with local Chroma and disk storage), ship a buildable container, and keep the no-env-var local mode behaving as before, except for the one labeled score fix (D12).

**Architecture:**
- A frozen `Settings` object is read once from the environment and validated at startup.
- `get_llm()` and `get_embeddings()` pick Ollama or Vertex, with Google imports only inside the Vertex branch.
- Services stop constructing Ollama clients themselves and share one instance of each dependency.
- Two behavior fixes ride along as separate commits: removing the duplicate embedding pass (D7) and normalizing similarity scores (D12).

**Tech Stack:** Python 3.13, FastAPI, langchain-core 1.6, langchain-ollama 1.1, langchain-chroma 1.0 + chromadb 1.0.20, langchain-google-genai 4.4.1 (optional `cloud` extra), pytest + pytest-asyncio (auto mode), uv 0.8.8, Docker, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-10-12-gcp-deployment-design.md` (sections "Configuration", "M2a", decisions D3, D7, D8, D9, D10, D11, D12)

## Global Constraints

- With no env vars set, behavior matches today, except D12 (scores), which is its own commit labeled as changing local output.
- Do not change prompts, chunking parameters (1,000 chars / 200 overlap), or API response shapes.
- `VERTEX_LLM_MODEL` and `VERTEX_EMBED_MODEL` are required when `LLM_PROVIDER=vertex`, with no default (D3). `GOOGLE_CLOUD_PROJECT` is also required then.
- No Gemini API keys anywhere. If `GOOGLE_API_KEY` or `GEMINI_API_KEY` is set (non-empty) while `LLM_PROVIDER=vertex`, startup fails.
- Google packages are imported only inside Vertex branches and live in the optional `cloud` extra. A plain `uv sync` must not install them, and the app must import without them.
- `max_tokens` is never passed to the model (D11). `VERTEX_THINKING_BUDGET` is passed only when set.
- Never use `loop.run_in_executor` for LLM or store calls (D8). Use `ainvoke`.
- Keep existing module singletons patchable: tests patch `app.services.flashcard_service.llm_service` and `app.services.qa_service.llm_service` (D9).
- The `CORS_ORIGINS` default is `http://localhost:3000,http://localhost:3001,http://127.0.0.1:3000,http://127.0.0.1:3001,null`. `*` is rejected (D10).
- `chromadb==1.0.20` stays pinned. Do not run `uv lock --upgrade`.
- Run commands from `backend/` unless stated otherwise.
- Commit messages end with:
  ```
  Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_018KkrpaKskjiWpMfynhy8W7
  ```
- Docker is **not installed** on the dev machine. The image is verified only by the CI `docker` job (Task 8).

## Review Focus

1. **Empty env vars** (`export GOOGLE_API_KEY=`, `CORS_ORIGINS=""`) are treated as unset and must not trip the API-key guard or produce an empty origin list. Tested in Task 1.
2. **Malformed values:** `VERTEX_THINKING_BUDGET=abc` must give a clear `ConfigError`, not a `ValueError` traceback. `LLM_PROVIDER=Vertex` is accepted case-insensitively. Tested in Task 1.
3. **Electron's `Origin: null`** must still be allowed after `*` is removed. Tested in Task 7.
4. **The container starts with zero env vars** and serves `/health` on a non-default `$PORT`. Tested in Task 8 (CI docker job).
5. **Non-unit embedding vectors** (Vertex with a reduced `output_dimensionality`, or an unfamiliar Ollama model) must still give scores in [0, 1] with closer chunks scoring higher. Tested in Task 6 with deliberately non-unit vectors.

---

### Task 1: Settings module (`app/core/config.py`)

**Files:**
- Create: `backend/app/core/__init__.py` (empty, if missing)
- Modify: `backend/app/core/config.py` (currently empty)
- Test: `backend/app/tests/test_config.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `class ConfigError(Exception)`
  - `@dataclass(frozen=True) class Settings` with fields `llm_provider: str`, `ollama_llm_model: str`, `ollama_embed_model: str`, `vertex_llm_model: Optional[str]`, `vertex_embed_model: Optional[str]`, `vertex_thinking_budget: Optional[int]`, `google_cloud_project: Optional[str]`, `google_cloud_location: str`, `upload_dir: str`, `chroma_dir: str`, `cors_origins: Tuple[str, ...]`
  - properties `Settings.llm_model -> str` and `Settings.embed_model -> str` (the active provider's model)
  - `Settings.from_env(env: Mapping[str, str]) -> Settings` (raises `ConfigError`)
  - `get_settings() -> Settings` (cached, reads `os.environ`)
  - `DEFAULT_CORS_ORIGINS: Tuple[str, ...]`

- [ ] **Step 1: Write the failing tests**

Create `backend/app/tests/test_config.py`:

```python
import pytest

from app.core.config import DEFAULT_CORS_ORIGINS, ConfigError, Settings

VERTEX_OK = {
    "LLM_PROVIDER": "vertex",
    "VERTEX_LLM_MODEL": "gemini-test-flash",
    "VERTEX_EMBED_MODEL": "gemini-embedding-001",
    "GOOGLE_CLOUD_PROJECT": "demo-project",
}


def test_empty_env_reproduces_local_defaults():
    s = Settings.from_env({})
    assert s.llm_provider == "ollama"
    assert s.llm_model == "gpt-oss:20b"
    assert s.embed_model == "nomic-embed-text"
    assert s.chroma_dir == "./chroma_db"
    assert s.upload_dir == "uploads"
    assert s.vertex_thinking_budget is None


def test_default_cors_includes_electron_production_origin():
    s = Settings.from_env({})
    assert s.cors_origins == DEFAULT_CORS_ORIGINS
    assert "http://127.0.0.1:3001" in s.cors_origins
    assert "null" in s.cors_origins


def test_vertex_settings_select_vertex_models():
    s = Settings.from_env(VERTEX_OK)
    assert s.llm_provider == "vertex"
    assert s.llm_model == "gemini-test-flash"
    assert s.embed_model == "gemini-embedding-001"
    assert s.google_cloud_location == "us-central1"


def test_provider_is_case_insensitive():
    assert Settings.from_env({**VERTEX_OK, "LLM_PROVIDER": "Vertex"}).llm_provider == "vertex"


def test_vertex_without_models_or_project_reports_every_missing_var():
    with pytest.raises(ConfigError) as exc:
        Settings.from_env({"LLM_PROVIDER": "vertex"})
    msg = str(exc.value)
    assert "VERTEX_LLM_MODEL" in msg
    assert "VERTEX_EMBED_MODEL" in msg
    assert "GOOGLE_CLOUD_PROJECT" in msg


def test_unknown_provider_rejected():
    with pytest.raises(ConfigError, match="LLM_PROVIDER"):
        Settings.from_env({"LLM_PROVIDER": "openai"})


@pytest.mark.parametrize("key_var", ["GOOGLE_API_KEY", "GEMINI_API_KEY"])
def test_api_key_with_vertex_rejected(key_var):
    with pytest.raises(ConfigError, match=key_var):
        Settings.from_env({**VERTEX_OK, key_var: "abc123"})


def test_empty_api_key_var_is_treated_as_unset():
    s = Settings.from_env({**VERTEX_OK, "GOOGLE_API_KEY": "", "GEMINI_API_KEY": "  "})
    assert s.llm_provider == "vertex"


def test_thinking_budget_parsed_when_set():
    assert Settings.from_env({**VERTEX_OK, "VERTEX_THINKING_BUDGET": "512"}).vertex_thinking_budget == 512


def test_non_integer_thinking_budget_is_config_error():
    with pytest.raises(ConfigError, match="VERTEX_THINKING_BUDGET"):
        Settings.from_env({**VERTEX_OK, "VERTEX_THINKING_BUDGET": "abc"})


def test_cors_origins_parsed_and_trimmed():
    s = Settings.from_env({"CORS_ORIGINS": " https://a.example , https://b.example ,"})
    assert s.cors_origins == ("https://a.example", "https://b.example")


def test_empty_cors_origins_falls_back_to_default():
    assert Settings.from_env({"CORS_ORIGINS": ""}).cors_origins == DEFAULT_CORS_ORIGINS


def test_wildcard_cors_rejected():
    with pytest.raises(ConfigError, match=r"\*"):
        Settings.from_env({"CORS_ORIGINS": "http://localhost:3000,*"})


def test_all_problems_reported_together():
    with pytest.raises(ConfigError) as exc:
        Settings.from_env({"LLM_PROVIDER": "vertex", "CORS_ORIGINS": "*", "VERTEX_THINKING_BUDGET": "x"})
    msg = str(exc.value)
    for fragment in ("VERTEX_LLM_MODEL", "CORS_ORIGINS", "VERTEX_THINKING_BUDGET"):
        assert fragment in msg
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest -p no:cacheprovider -q app/tests/test_config.py`
Expected: collection error, `ImportError: cannot import name 'DEFAULT_CORS_ORIGINS' from 'app.core.config'` (the file is empty).

- [ ] **Step 3: Implement `backend/app/core/config.py`**

If `backend/app/core/__init__.py` does not exist, create it empty. Then write `backend/app/core/config.py`:

```python
"""Application settings read from environment variables.

With no environment variables set, the defaults reproduce the original fully
local setup: Ollama for the LLM and embeddings, Chroma on local disk.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import List, Mapping, Optional, Tuple

DEFAULT_CORS_ORIGINS: Tuple[str, ...] = (
    "http://localhost:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",  # packaged Electron app
    "null",  # Electron file:// requests
)
LLM_PROVIDERS = ("ollama", "vertex")
# The google-genai SDK silently switches from Vertex/ADC to API-key mode when these are set.
API_KEY_VARS = ("GOOGLE_API_KEY", "GEMINI_API_KEY")


class ConfigError(Exception):
    """Raised when the environment describes an invalid configuration."""


@dataclass(frozen=True)
class Settings:
    llm_provider: str = "ollama"
    ollama_llm_model: str = "gpt-oss:20b"
    ollama_embed_model: str = "nomic-embed-text"
    vertex_llm_model: Optional[str] = None
    vertex_embed_model: Optional[str] = None
    vertex_thinking_budget: Optional[int] = None
    google_cloud_project: Optional[str] = None
    google_cloud_location: str = "us-central1"
    upload_dir: str = "uploads"
    chroma_dir: str = "./chroma_db"
    cors_origins: Tuple[str, ...] = DEFAULT_CORS_ORIGINS

    @property
    def llm_model(self) -> str:
        return self.vertex_llm_model if self.llm_provider == "vertex" else self.ollama_llm_model

    @property
    def embed_model(self) -> str:
        return self.vertex_embed_model if self.llm_provider == "vertex" else self.ollama_embed_model

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> "Settings":
        def get(name: str) -> Optional[str]:
            value = (env.get(name) or "").strip()
            return value or None

        problems: List[str] = []

        provider = (get("LLM_PROVIDER") or "ollama").lower()
        if provider not in LLM_PROVIDERS:
            problems.append(f"LLM_PROVIDER must be one of {', '.join(LLM_PROVIDERS)}, got {provider!r}")

        thinking_budget: Optional[int] = None
        raw_budget = get("VERTEX_THINKING_BUDGET")
        if raw_budget is not None:
            try:
                thinking_budget = int(raw_budget)
            except ValueError:
                problems.append(f"VERTEX_THINKING_BUDGET must be an integer, got {raw_budget!r}")

        raw_cors = get("CORS_ORIGINS")
        if raw_cors is None:
            cors_origins = DEFAULT_CORS_ORIGINS
        else:
            cors_origins = tuple(origin.strip() for origin in raw_cors.split(",") if origin.strip())
            if "*" in cors_origins:
                problems.append("CORS_ORIGINS must not contain '*'; list the allowed origins explicitly")

        if provider == "vertex":
            for name in ("VERTEX_LLM_MODEL", "VERTEX_EMBED_MODEL", "GOOGLE_CLOUD_PROJECT"):
                if get(name) is None:
                    problems.append(f"{name} is required when LLM_PROVIDER=vertex")
            for name in API_KEY_VARS:
                if get(name) is not None:
                    problems.append(
                        f"{name} must not be set when LLM_PROVIDER=vertex; "
                        "Vertex uses Application Default Credentials, not API keys"
                    )

        if problems:
            raise ConfigError("Invalid configuration:\n" + "\n".join(f"  - {p}" for p in problems))

        return cls(
            llm_provider=provider,
            ollama_llm_model=get("OLLAMA_LLM_MODEL") or cls.ollama_llm_model,
            ollama_embed_model=get("OLLAMA_EMBED_MODEL") or cls.ollama_embed_model,
            vertex_llm_model=get("VERTEX_LLM_MODEL"),
            vertex_embed_model=get("VERTEX_EMBED_MODEL"),
            vertex_thinking_budget=thinking_budget,
            google_cloud_project=get("GOOGLE_CLOUD_PROJECT"),
            google_cloud_location=get("GOOGLE_CLOUD_LOCATION") or cls.google_cloud_location,
            upload_dir=get("UPLOAD_DIR") or cls.upload_dir,
            chroma_dir=get("CHROMA_DIR") or cls.chroma_dir,
            cors_origins=cors_origins,
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Settings for this process, read from os.environ once. Raises ConfigError."""
    return Settings.from_env(os.environ)
```

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest -p no:cacheprovider -q app/tests/test_config.py 2>&1 | tail -1`
Expected: `15 passed` (14 test functions, one parametrized twice).
Then run the whole suite: `uv run pytest -p no:cacheprovider -q 2>&1 | tail -1`. Expected: `53 passed, 3 deselected`.

- [ ] **Step 5: Commit**

```bash
git add app/core/__init__.py app/core/config.py app/tests/test_config.py
git commit -m "Add environment-based settings with startup validation

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_018KkrpaKskjiWpMfynhy8W7"
```

---

### Task 2: Provider factories and the `cloud` extra

**Files:**
- Create: `backend/app/core/providers.py`
- Modify: `backend/pyproject.toml` (add the `[project.optional-dependencies]` table)
- Modify: `backend/uv.lock` (regenerated)
- Test: `backend/app/tests/test_providers.py`

**Interfaces:**
- Consumes: `Settings`, `get_settings()` (Task 1).
- Produces:
  - `get_llm(temperature: float, model: Optional[str] = None, settings: Optional[Settings] = None)`, which returns `OllamaLLM` or `ChatGoogleGenerativeAI`
  - `get_embeddings(model: Optional[str] = None, settings: Optional[Settings] = None) -> Embeddings`, which returns `OllamaEmbeddings` or `GoogleGenerativeAIEmbeddings`

- [ ] **Step 1: Write the failing tests**

Create `backend/app/tests/test_providers.py`:

```python
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
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest -p no:cacheprovider -q app/tests/test_providers.py 2>&1 | tail -3`
Expected: collection error, `ModuleNotFoundError: No module named 'app.core.providers'`.

- [ ] **Step 3: Implement `backend/app/core/providers.py`**

```python
"""Factories for the LLM and embedding clients selected by LLM_PROVIDER.

Google packages are imported only inside the vertex branches, so a local install
without the `cloud` extra imports this module (and the app) cleanly.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from langchain_core.embeddings import Embeddings

from .config import Settings, get_settings


def get_llm(temperature: float, model: Optional[str] = None, settings: Optional[Settings] = None):
    """LLM client for the configured provider. `max_tokens` is deliberately not passed (spec D11)."""
    s = settings or get_settings()
    if s.llm_provider == "vertex":
        from langchain_google_genai import ChatGoogleGenerativeAI

        kwargs: Dict[str, Any] = {
            "model": model or s.vertex_llm_model,
            "project": s.google_cloud_project,
            "location": s.google_cloud_location,
            "vertexai": True,  # Vertex AI backend with Application Default Credentials; never an API key
            "temperature": temperature,
        }
        if s.vertex_thinking_budget is not None:
            kwargs["thinking_budget"] = s.vertex_thinking_budget
        return ChatGoogleGenerativeAI(**kwargs)

    from langchain_ollama import OllamaLLM

    return OllamaLLM(model=model or s.ollama_llm_model, temperature=temperature)


def get_embeddings(model: Optional[str] = None, settings: Optional[Settings] = None) -> Embeddings:
    """Embedding client for the configured provider.

    Vertex and Ollama vectors have different dimensions. Never write both into the same
    collection: local and cloud deployments use separate Chroma directories / databases.
    """
    s = settings or get_settings()
    if s.llm_provider == "vertex":
        from langchain_google_genai import GoogleGenerativeAIEmbeddings

        return GoogleGenerativeAIEmbeddings(
            model=model or s.vertex_embed_model,
            project=s.google_cloud_project,
            location=s.google_cloud_location,
            vertexai=True,
        )

    from langchain_ollama import OllamaEmbeddings

    return OllamaEmbeddings(model=model or s.ollama_embed_model)
```

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest -p no:cacheprovider -q app/tests/test_providers.py 2>&1 | tail -1`
Expected: `8 passed`.

- [ ] **Step 5: Add the `cloud` extra and relock**

In `backend/pyproject.toml`, add after the `dependencies = [...]` array:

```toml
[project.optional-dependencies]
cloud = [
    "langchain-google-genai>=4.4.1,<5",
]
```

Then:
```bash
uv lock
grep -A1 '^name = "chromadb"$' uv.lock | tail -1      # Expected: version = "1.0.20"
grep -A1 '^name = "langchain-google-genai"$' uv.lock | tail -1   # Expected: version = "4.4.1" (or a later 4.x)
uv sync --locked && uv run python -c "import langchain_google_genai" 2>&1 | tail -1
```
Expected for the last line: `ModuleNotFoundError: No module named 'langchain_google_genai'`. A plain sync must not install the extra.

- [ ] **Step 6: Run the full suite**

Run: `uv run pytest -p no:cacheprovider -q 2>&1 | tail -1`
Expected: `61 passed, 3 deselected`.

- [ ] **Step 7: Commit**

```bash
git add app/core/providers.py app/tests/test_providers.py pyproject.toml uv.lock
git commit -m "Add Ollama/Vertex provider factories and optional cloud extra

Vertex uses langchain-google-genai's ChatGoogleGenerativeAI and
GoogleGenerativeAIEmbeddings with vertexai=True (ADC, no API keys).
Google packages are imported lazily and only installed with --extra cloud.

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_018KkrpaKskjiWpMfynhy8W7"
```

---

### Task 3: Services use the providers; `ainvoke` + text normalization; fail fast at startup

**Files:**
- Modify: `backend/app/services/llm_service.py` (imports at lines 1-7, `__init__` at lines 13-23, `_generate_response` at about lines 778-792)
- Modify: `backend/app/services/embedding.py` (import at line 2, `__init__` at lines 23-32)
- Modify: `backend/app/services/vector_store.py` (imports at lines 2-3, `__init__` at lines 15-25)
- Modify: `backend/app/services/document.py` (`__init__` at lines 20-27)
- Modify: `backend/app/main.py` (top of file)
- Test: `backend/app/tests/test_llm_service.py`, `backend/app/tests/test_startup.py`

**Interfaces:**
- Consumes: `get_settings()`, `ConfigError` (Task 1); `get_llm()`, `get_embeddings()` (Task 2).
- Produces:
  - `LLMService(model_name: Optional[str] = None, temperature: float = 0.7, max_tokens: int = 2048)`
  - `EmbeddingService(model_name: Optional[str] = None, batch_size=10, max_retries=3, retry_delay=1.0)`
  - `VectorStoreService(persist_directory: Optional[str] = None, embedding_model: Optional[str] = None, collection_name: str = "documents", embeddings: Optional[Embeddings] = None)`, where `embeddings` is used by Task 6's test
  - `DocumentService(upload_dir: Optional[str] = None, ...)`

- [ ] **Step 1: Write the failing tests**

Create `backend/app/tests/test_llm_service.py`:

```python
import pytest
from langchain_core.messages import AIMessage

import app.services.llm_service as llm_mod
from app.core.config import Settings
from app.services.llm_service import LLMService


class FakeLLM:
    """Async-only fake: any use of the sync invoke() path fails the test (spec D8)."""

    def __init__(self, result):
        self.result = result
        self.prompts = []

    async def ainvoke(self, prompt):
        self.prompts.append(prompt)
        return self.result

    def invoke(self, prompt):
        raise AssertionError("LLMService must call ainvoke, not invoke via an executor")


def service_returning(result) -> LLMService:
    svc = LLMService()
    svc.llm = FakeLLM(result)
    return svc


async def test_plain_string_response_is_stripped():
    assert await service_returning("  Model is working \n")._generate_response("p") == "Model is working"


async def test_chat_message_response_is_normalized_to_text():
    msg = AIMessage(content="  An answer.  ")
    assert await service_returning(msg)._generate_response("p") == "An answer."


async def test_thinking_parts_are_dropped_from_list_content():
    msg = AIMessage(content=[
        {"type": "thinking", "thinking": "internal reasoning"},
        {"type": "text", "text": " Final answer. "},
    ])
    assert await service_returning(msg)._generate_response("p") == "Final answer."


async def test_prompt_is_passed_through_unchanged():
    svc = service_returning("ok")
    await svc._generate_response("exact prompt {x1}")
    assert svc.llm.prompts == ["exact prompt {x1}"]


def test_default_model_comes_from_active_provider(monkeypatch):
    vertex = Settings.from_env({"LLM_PROVIDER": "vertex", "VERTEX_LLM_MODEL": "gemini-test-flash",
                                "VERTEX_EMBED_MODEL": "e", "GOOGLE_CLOUD_PROJECT": "p"})
    calls = []
    monkeypatch.setattr(llm_mod, "get_settings", lambda: vertex)
    monkeypatch.setattr(llm_mod, "get_llm", lambda temperature, model=None: calls.append((temperature, model)) or object())
    svc = LLMService(temperature=0.4)
    assert svc.model_name == "gemini-test-flash"
    assert calls == [(0.4, "gemini-test-flash")]


def test_local_default_model_unchanged():
    assert LLMService().model_name == "gpt-oss:20b"
```

Create `backend/app/tests/test_startup.py`:

```python
import os
import subprocess
import sys


def test_invalid_config_stops_startup_with_readable_message():
    env = {k: v for k, v in os.environ.items() if not k.startswith(("VERTEX_", "GOOGLE_", "GEMINI_"))}
    env["LLM_PROVIDER"] = "vertex"
    out = subprocess.run([sys.executable, "-c", "import app.main"], env=env, capture_output=True, text=True)
    assert out.returncode != 0
    assert "VERTEX_LLM_MODEL is required when LLM_PROVIDER=vertex" in out.stderr
    assert "Traceback" not in out.stderr
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest -p no:cacheprovider -q app/tests/test_llm_service.py app/tests/test_startup.py 2>&1 | tail -12`
Expected failures:
- the three response tests fail with `AssertionError: LLMService must call ainvoke...` (raised from inside the executor);
- `test_default_model_comes_from_active_provider` fails with `AttributeError` (`llm_mod` has no `get_settings`);
- `test_invalid_config_stops_startup_with_readable_message` fails because `import app.main` succeeds (returncode 0).

`test_local_default_model_unchanged` passes already. It pins existing behavior.

- [ ] **Step 3: Update `backend/app/services/llm_service.py`**

Replace the imports at the top (lines 1-7):

```python
# LLM service for generating answers with the configured provider (Ollama or Vertex AI)
from typing import Dict, Any, Optional, List
import logging
import json

from langchain_core.messages import BaseMessage

from ..core.config import get_settings
from ..core.providers import get_llm
```

Keep `import asyncio` only if `grep -n "asyncio\." app/services/llm_service.py` still shows uses after Step 3 is done. Otherwise remove it.

Replace `__init__` (lines 13-23):

```python
    def __init__(self, model_name: Optional[str] = None,
                 temperature: float = 0.7,
                 max_tokens: int = 2048):
        self.model_name = model_name or get_settings().llm_model
        self.temperature = temperature
        self.max_tokens = max_tokens  # reported by validate_model; not sent to the model (spec D11)
        self.llm = get_llm(temperature, model=self.model_name)
        logger.info(f"Initialized LLM service with model: {self.model_name}")
```

Replace the body of `_generate_response`:

```python
    async def _generate_response(self, prompt: str) -> str:
        """Generate a response using the LLM"""
        try:
            response = await self.llm.ainvoke(prompt)
            # OllamaLLM returns str; chat models return a message whose .text joins only text parts
            text = response.text if isinstance(response, BaseMessage) else response
            return text.strip()

        except Exception as e:
            logger.error(f"Error in LLM response generation: {str(e)}")
            raise
```

Also update the class docstring on line 11 to `"""Service for generating answers with the configured LLM provider"""`. Do not touch any prompt text.

- [ ] **Step 4: Update `backend/app/services/embedding.py`**

Replace `from langchain_ollama import OllamaEmbeddings` (line 2) with:

```python
from ..core.config import get_settings
from ..core.providers import get_embeddings
```

Replace the start of `__init__`:

```python
    def __init__(self, model_name: Optional[str] = None,
                 batch_size: int = 10,
                 max_retries: int = 3,
                 retry_delay: float = 1.0):
        self.model_name = model_name or get_settings().embed_model
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.embeddings = get_embeddings(model=self.model_name)
        logger.info(f"Initialized embedding service with model: {self.model_name}")
```

Update the class docstring to `"""Service for generating embeddings with the configured provider"""`.

- [ ] **Step 5: Update `backend/app/services/vector_store.py`**

Replace `from langchain_ollama import OllamaEmbeddings` (line 3) with:

```python
from langchain_core.embeddings import Embeddings

from ..core.config import get_settings
from ..core.providers import get_embeddings
```

Replace `__init__`:

```python
    def __init__(self,
                 persist_directory: Optional[str] = None,
                 embedding_model: Optional[str] = None,
                 collection_name: str = "documents",
                 embeddings: Optional[Embeddings] = None):
        settings = get_settings()
        self.persist_directory = Path(persist_directory or settings.chroma_dir)
        self.persist_directory.mkdir(exist_ok=True)
        self.embedding_model = embedding_model or settings.embed_model
        self.collection_name = collection_name
        # One collection must only ever hold vectors from one embedding model: Vertex and
        # nomic-embed-text vectors differ in dimension. Use a separate CHROMA_DIR per provider.
        self.embeddings = embeddings or get_embeddings(model=self.embedding_model)
        self.vector_store = None
        self._initialize_vector_store()
        logger.info(f"Initialized vector store service with directory: {self.persist_directory}")
```

- [ ] **Step 6: Update `backend/app/services/document.py`**

Add `from ..core.config import get_settings` after the existing relative imports. Change the `__init__` signature and first line:

```python
    def __init__(self, upload_dir: Optional[str] = None,
                 large_document_threshold: int = 5000,  # characters
                 chunk_size: int = 1000,
                 chunk_overlap: int = 200):
        self.upload_dir = Path(upload_dir or get_settings().upload_dir)
```

The rest of `__init__` is unchanged.

- [ ] **Step 7: Fail fast in `backend/app/main.py`**

Insert at the very top of the file, before `from fastapi import FastAPI`:

```python
from .core.config import ConfigError, get_settings

try:
    # Validate configuration before any service is constructed (services build clients at import).
    settings = get_settings()
except ConfigError as exc:
    raise SystemExit(str(exc)) from None
```

- [ ] **Step 8: Run to verify they pass**

```bash
uv run pytest -p no:cacheprovider -q app/tests/test_llm_service.py app/tests/test_startup.py 2>&1 | tail -1
grep -rn "run_in_executor\|OllamaLLM(\|OllamaEmbeddings(" app --include='*.py' | grep -v "app/core/providers.py\|app/tests/"
uv run pytest -p no:cacheprovider -q 2>&1 | tail -1
```
Expected:
- `7 passed` for the two new files.
- The grep prints nothing, so no direct Ollama construction or executor remains outside `providers.py`.
- The full suite reports `68 passed, 3 deselected`.

- [ ] **Step 9: Commit**

```bash
git add app/services/llm_service.py app/services/embedding.py app/services/vector_store.py app/services/document.py app/main.py app/tests/test_llm_service.py app/tests/test_startup.py
git commit -m "Route services through provider factories and validate config at startup

LLMService now awaits llm.ainvoke and normalizes chat messages via
.text, so Gemini responses (including thinking parts) become plain
strings. Model names, CHROMA_DIR and UPLOAD_DIR come from settings.

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_018KkrpaKskjiWpMfynhy8W7"
```

---

### Task 4: Shared service instances (D9)

**Files:**
- Modify: `backend/app/services/document.py` (add a module singleton at the end of the file)
- Modify: `backend/app/services/qa_service.py:32` and `__init__` (about line 91)
- Modify: `backend/app/services/quiz_service.py:26` and `__init__` (about line 67)
- Modify: `backend/app/services/flashcard_service.py:10` and `__init__` (line 19)
- Modify: `backend/app/services/rag_pipeline.py` (imports at lines 6-9, `__init__` at lines 15-23)
- Modify: `backend/app/api/routes/files.py` (lines 7 and 16)
- Test: `backend/app/tests/test_wiring.py`

**Interfaces:**
- Consumes: the constructors from Task 3.
- Produces: `app.services.document.document_service: DocumentService`, the one shared instance. Every service whose constructor previously did `x or XService()` now defaults to the shared module singleton.

- [ ] **Step 1: Write the failing tests**

Create `backend/app/tests/test_wiring.py`:

```python
from app.api.routes import files
from app.services import (
    document,
    embedding,
    flashcard_service,
    qa_service,
    quiz_service,
    rag_pipeline,
    vector_store,
)


def test_every_consumer_shares_one_document_service():
    shared = document.document_service
    assert qa_service.qa_service.document_service is shared
    assert quiz_service.quiz_service.document_service is shared
    assert flashcard_service.flashcard_service.document_service is shared
    assert rag_pipeline.rag_pipeline_service.document_service is shared
    assert files.document_service is shared


def test_pipeline_shares_embedding_and_vector_store_singletons():
    pipeline = rag_pipeline.rag_pipeline_service
    assert pipeline.embedding_service is embedding.embedding_service
    assert pipeline.vector_store_service is vector_store.vector_store_service


def test_explicit_dependencies_still_win():
    sentinel = object()
    assert qa_service.QAService(document_service=sentinel, use_llm=False).document_service is sentinel
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest -p no:cacheprovider -q app/tests/test_wiring.py 2>&1 | tail -4`
Expected: the first test fails with `AttributeError: module 'app.services.document' has no attribute 'document_service'`, and the second fails on `is` (the pipeline built its own instances). The third passes already (existing behavior).

- [ ] **Step 3: Implement**

`backend/app/services/document.py`, append at the end of the file:

```python

# Shared instance: every service and route uses this one (spec D9)
document_service = DocumentService()
```

`backend/app/services/qa_service.py`: change line 32 `from .document import DocumentService` to:

```python
from .document import DocumentService, document_service as shared_document_service
```

and in `__init__` change `self.document_service = document_service or DocumentService()` to:

```python
        self.document_service = document_service or shared_document_service
```

`backend/app/services/quiz_service.py` and `backend/app/services/flashcard_service.py` get exactly the same two edits: the import line, and `document_service or shared_document_service` in `__init__`.

`backend/app/services/rag_pipeline.py`: replace the three service imports with:

```python
from .document import DocumentService, document_service as shared_document_service
from .embedding import EmbeddingService, EmbeddingResult, embedding_service as shared_embedding_service
from .vector_store import VectorStoreService, vector_store_service as shared_vector_store_service
```

and in `__init__`:

```python
        self.document_service = document_service or shared_document_service
        self.embedding_service = embedding_service or shared_embedding_service
        self.vector_store_service = vector_store_service or shared_vector_store_service
```

`backend/app/api/routes/files.py`: change `from ...services.document import DocumentService` to `from ...services.document import document_service`, and delete line 16 (`document_service = DocumentService()`) together with its `# Initialize document service` comment.

- [ ] **Step 4: Run to verify it passes**

```bash
uv run pytest -p no:cacheprovider -q app/tests/test_wiring.py 2>&1 | tail -1
uv run pytest -p no:cacheprovider -q 2>&1 | tail -1
```
Expected: `3 passed`, then `71 passed, 3 deselected`. The existing `patch('app.services.flashcard_service.llm_service', ...)` tests in `test_flashcards.py` still pass.

- [ ] **Step 5: Commit**

```bash
git add app/services/document.py app/services/qa_service.py app/services/quiz_service.py app/services/flashcard_service.py app/services/rag_pipeline.py app/api/routes/files.py app/tests/test_wiring.py
git commit -m "Share one instance of each service dependency

QA, quiz, flashcards, the RAG pipeline and the files routes each built
their own DocumentService (and the pipeline its own embedding and
vector store). They now default to the shared module singletons.

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_018KkrpaKskjiWpMfynhy8W7"
```

---

### Task 5: Remove the duplicate embedding pass (D7)

**Files:**
- Modify: `backend/app/services/rag_pipeline.py` (`process_document_upload` Steps 3-5, about lines 40-85; delete `_generate_embeddings_for_chunks`, about lines 137-168)
- Test: `backend/app/tests/test_rag_pipeline.py`

**Interfaces:**
- Consumes: `RAGPipelineService(document_service, embedding_service, vector_store_service)` (Task 4).
- Produces: an unchanged response shape. The `embedding` keys are `enabled, success, total_embeddings, successful_embeddings, failed_embeddings`, and the `vector_storage` keys are `success, documents_stored`.

- [ ] **Step 1: Write the failing tests**

Create `backend/app/tests/test_rag_pipeline.py`:

```python
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
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest -p no:cacheprovider -q app/tests/test_rag_pipeline.py 2>&1 | tail -5`
Expected:
- `test_chunks_are_embedded_once_by_the_vector_store_only` fails on `embed_batch.await_count == 0` (it is 1);
- `test_store_failure_reports_failed_embeddings_like_before` fails because, with the mocked `embed_batch` returning `[]`, the store is never called and the counts differ;
- `test_embedding_disabled_skips_vector_store` passes already (existing behavior).

- [ ] **Step 3: Implement**

In `process_document_upload`, replace the current "Step 3: Generate embeddings" and "Step 4: Store in vector database" blocks with:

```python
            # Step 3: Embed and store (the vector store embeds each chunk exactly once; spec D7)
            vector_store_result = None
            if enable_embedding and chunks:
                logger.info("Step 3: Embedding chunks and storing them in the vector database")
                vector_store_result = await self._store_chunks_in_vector_db(chunks, file_id)

            attempted = len(chunks) if vector_store_result is not None else 0
            stored = vector_store_result.get('documents_added', 0) if vector_store_result and vector_store_result.get('success') else 0
```

and replace the `"embedding": {...}` entry of the result dict with:

```python
                "embedding": {
                    "enabled": enable_embedding,
                    "success": vector_store_result is not None,
                    "total_embeddings": attempted,
                    "successful_embeddings": stored,
                    "failed_embeddings": attempted - stored
                },
```

Leave the `"vector_storage"` entry as it is. It already reads `vector_store_result`. Renumber the "Step 5: Compile final result" comment to "Step 4". Delete the now-unused `_generate_embeddings_for_chunks` method. Check that nothing else calls it:

```bash
grep -rn "_generate_embeddings_for_chunks\|embedding_results" app/services/rag_pipeline.py
```
Expected: no output (no leftover references to the removed embedding pass).

- [ ] **Step 4: Run to verify it passes**

```bash
uv run pytest -p no:cacheprovider -q app/tests/test_rag_pipeline.py 2>&1 | tail -1
uv run pytest -p no:cacheprovider -q 2>&1 | tail -1
```
Expected: `3 passed`, then `74 passed, 3 deselected`.

- [ ] **Step 5: Commit**

```bash
git add app/services/rag_pipeline.py app/tests/test_rag_pipeline.py
git commit -m "Embed uploaded chunks once instead of twice

The pipeline embedded every chunk through EmbeddingService, discarded
the vectors, then the vector store embedded the same text again. Only
the store embeds now, which halves embedding calls (and Vertex cost).
The upload response keeps its shape; counts come from the store result.

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_018KkrpaKskjiWpMfynhy8W7"
```

---

### Task 6: Similarity scores as 0-1 relevance (D12), a bug fix that changes local output

**Files:**
- Modify: `backend/app/services/vector_store.py` (add helpers above the class; wrap embeddings in `__init__`; convert the score in `search_similar`)
- Test: `backend/app/tests/test_vector_store_scores.py`

**Interfaces:**
- Consumes: `VectorStoreService(..., embeddings=...)` (Task 3).
- Produces:
  - `UnitNormalizedEmbeddings(base: Embeddings)`
  - `chroma_distance_to_relevance(distance: float) -> float`
  - `search_similar(...)` results with `similarity_score` in [0, 1], higher = more relevant. M2b adds the pgvector conversion next to the Chroma one.

**Why the wrapper:** Chroma's default space is squared L2. For unit vectors, `d = 2 - 2·cos`, so `relevance = 1 - d/2` is exactly the cosine similarity. Ollama's `/api/embed` and Vertex's full-size embeddings are already unit length, so the wrapper is a no-op for them apart from float rounding. Vertex with a reduced `output_dimensionality`, or an arbitrary Ollama model, may not be, and the wrapper guarantees the formula holds.

- [ ] **Step 1: Write the failing test**

Create `backend/app/tests/test_vector_store_scores.py`:

```python
import math

from langchain_core.embeddings import Embeddings

from app.services.vector_store import VectorStoreService, chroma_distance_to_relevance

# Deliberately NOT unit length, like Vertex vectors with a reduced output_dimensionality.
VECTORS = {
    "query": [3.0, 0.0, 0.0],
    "near": [2.0, 0.2, 0.0],
    "middle": [1.0, 1.0, 0.0],
    "far": [0.0, 0.0, 5.0],
}


class TableEmbeddings(Embeddings):
    def embed_documents(self, texts):
        return [VECTORS[t] for t in texts]

    def embed_query(self, text):
        return VECTORS[text]


def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    return dot / (math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b)))


async def test_closer_chunk_gets_higher_relevance_in_unit_range(tmp_path):
    store = VectorStoreService(persist_directory=str(tmp_path / "chroma"), embeddings=TableEmbeddings())
    await store.add_documents(
        texts=["near", "middle", "far"],
        metadatas=[{"file_id": "f", "chunk_id": name} for name in ("near", "middle", "far")],
        ids=["near", "middle", "far"],
    )
    results = await store.search_similar("query", k=3)
    scores = {r["id"]: r["similarity_score"] for r in results}

    assert all(0.0 <= s <= 1.0 for s in scores.values())
    assert scores["near"] > scores["middle"] > scores["far"]
    assert math.isclose(scores["near"], cosine(VECTORS["query"], VECTORS["near"]), abs_tol=1e-4)
    assert math.isclose(scores["far"], 0.0, abs_tol=1e-6)  # orthogonal -> cosine 0


def test_distance_conversion_is_clamped():
    assert chroma_distance_to_relevance(0.0) == 1.0
    assert chroma_distance_to_relevance(4.0) == 0.0   # opposite unit vectors
    assert chroma_distance_to_relevance(-1e-9) == 1.0  # float noise below zero
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest -p no:cacheprovider -q app/tests/test_vector_store_scores.py 2>&1 | tail -3`
Expected: collection error, `ImportError: cannot import name 'chroma_distance_to_relevance'`. Before writing the implementation, temporarily drop that name from the import and re-run to see the real behavioral failure: `assert scores["near"] > scores["middle"] > scores["far"]` fails, because today `similarity_score` is a raw distance (lower = closer). Restore the import afterwards.

- [ ] **Step 3: Implement in `backend/app/services/vector_store.py`**

Add `import math` to the imports. Add above `class VectorStoreService`:

```python
def _unit(vector: List[float]) -> List[float]:
    norm = math.sqrt(sum(x * x for x in vector))
    return [x / norm for x in vector] if norm else list(vector)


class UnitNormalizedEmbeddings(Embeddings):
    """Scales every vector to unit length, so a squared-L2 distance d equals 2 - 2*cosine.

    Ollama's /api/embed and full-size Vertex embeddings are already unit length; this
    guarantees it for reduced output dimensions and other models.
    """

    def __init__(self, base: Embeddings):
        self.base = base

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [_unit(v) for v in self.base.embed_documents(texts)]

    def embed_query(self, text: str) -> List[float]:
        return _unit(self.base.embed_query(text))

    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        return [_unit(v) for v in await self.base.aembed_documents(texts)]

    async def aembed_query(self, text: str) -> List[float]:
        return _unit(await self.base.aembed_query(text))


def chroma_distance_to_relevance(distance: float) -> float:
    """Chroma's default squared-L2 distance on unit vectors -> cosine similarity clamped to [0, 1]."""
    return max(0.0, min(1.0, 1.0 - distance / 2.0))
```

In `__init__`, change the embeddings line to:

```python
        self.embeddings = UnitNormalizedEmbeddings(embeddings or get_embeddings(model=self.embedding_model))
```

In `search_similar`, change `'similarity_score': float(score),` to:

```python
                    'similarity_score': chroma_distance_to_relevance(float(score)),
```

- [ ] **Step 4: Run to verify it passes**

```bash
uv run pytest -p no:cacheprovider -q app/tests/test_vector_store_scores.py 2>&1 | tail -1
uv run pytest -p no:cacheprovider -q 2>&1 | tail -1
```
Expected: `2 passed`, then `76 passed, 3 deselected`.

- [ ] **Step 5: Commit (labeled as a local-output change)**

```bash
git add app/services/vector_store.py app/tests/test_vector_store_scores.py
git commit -m "Fix similarity_score: return 0-1 relevance, higher is better

Bug fix that changes local output. Chroma returns a squared-L2
distance (lower = closer), but qa_service treats similarity_score as
relevance (higher = better) in _source_match_percent, the heuristic
grounding check, score bands, evidence refs and the confidence score,
so the closest chunks were scored as the weakest. Scores are now
cosine similarity clamped to [0, 1], computed on unit-normalized
vectors. Heatmap percentages, score bands and confidence values in
local mode change accordingly.

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_018KkrpaKskjiWpMfynhy8W7"
```

---

### Task 7: CORS from settings (D10)

**Files:**
- Modify: `backend/app/main.py` (the `app.add_middleware(CORSMiddleware, ...)` block)
- Test: `backend/app/tests/test_cors.py`

**Interfaces:**
- Consumes: `settings` (module global in `app/main.py`, Task 3) and `Settings.cors_origins` (Task 1).
- Produces: nothing new.

- [ ] **Step 1: Write the failing tests**

Create `backend/app/tests/test_cors.py`:

```python
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
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest -p no:cacheprovider -q app/tests/test_cors.py 2>&1 | tail -3`
Expected: `test_unlisted_origin_not_allowed` fails, because the hardcoded `"*"` with credentials echoes any origin. The four allowed-origin cases pass already.

- [ ] **Step 3: Implement**

In `backend/app/main.py`, replace the middleware block with:

```python
# Add CORS middleware (origins from CORS_ORIGINS; '*' is rejected at startup)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

- [ ] **Step 4: Run to verify it passes**

```bash
uv run pytest -p no:cacheprovider -q app/tests/test_cors.py 2>&1 | tail -1
uv run pytest -p no:cacheprovider -q 2>&1 | tail -1
```
Expected: `5 passed`, then `81 passed, 3 deselected`.

- [ ] **Step 5: Commit**

```bash
git add app/main.py app/tests/test_cors.py
git commit -m "Read CORS origins from settings and drop the wildcard

The hardcoded list included '*' alongside allow_credentials=True,
which let any origin through. The default now lists the dev servers,
the packaged Electron origin (127.0.0.1:3001) and 'null'.

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_018KkrpaKskjiWpMfynhy8W7"
```

---

### Task 8: Packaging, container, CI and docs

**Files:**
- Modify: `backend/pyproject.toml` (move dev tools into `[dependency-groups]`)
- Modify: `backend/uv.lock` (regenerated)
- Create: `backend/Dockerfile`, `backend/.dockerignore`
- Modify: `.github/workflows/backend.yml`
- Modify: `README.md` ("Environment Variables" section, about lines 126-134)
- Modify: `backend/RAG_PIPELINE_README.md` ("Required Packages", about lines 232-236)

**Interfaces:**
- Consumes: the `cloud` extra (Task 2); `PORT` handling via the container `CMD`.
- Produces: the `docker` CI job (M2b extends it).

- [ ] **Step 1: Move dev tools into a dependency group**

In `backend/pyproject.toml`, delete the `"pyinstaller>=6.15.0"`, `"pytest>=8.4.1"` and `"pytest-asyncio>=1.1.0"` lines from `dependencies`, and add at the end of the file:

```toml
[dependency-groups]
dev = [
    "pyinstaller>=6.15.0",
    "pytest>=8.4.1",
    "pytest-asyncio>=1.1.0",
]
```

Then:
```bash
uv lock && uv sync --locked
uv run pytest -p no:cacheprovider -q 2>&1 | tail -1
uv export --frozen --no-dev --extra cloud --no-hashes | grep -ciE "^(pyinstaller|pytest)" ; true
uv export --frozen --no-dev --extra cloud --no-hashes | grep -iE "^(chromadb|langchain-google-genai)=="
```
Expected:
- the suite reports `81 passed, 3 deselected`, because uv installs the `dev` group by default, so local and Electron builds are unaffected;
- the count of pyinstaller/pytest lines in the production export is `0`;
- the export lists `chromadb==1.0.20` and `langchain-google-genai==4.x`.

- [ ] **Step 2: Write `backend/Dockerfile`**

```dockerfile
FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:0.8.8 /uv /bin/uv

ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app
RUN useradd --create-home --uid 10001 app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --extra cloud --no-install-project

COPY app ./app
RUN chown -R app:app /app
USER app

EXPOSE 8080
CMD ["sh", "-c", "exec /app/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
```

- [ ] **Step 3: Write `backend/.dockerignore`**

```
.venv/
**/__pycache__/
.pytest_cache/
chroma_db/
uploads/
app/tests/
evals/results/
.env
.env.*
```

- [ ] **Step 4: Update `.github/workflows/backend.yml`**

Replace the whole file:

```yaml
name: backend

# Push only: a PR's head commit already has this push run, so PRs don't run it twice.
on:
  push:

permissions:
  contents: read

jobs:
  test:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: backend
    env:
      # No Ollama in CI. Point the client at a closed port so any stray call fails fast.
      OLLAMA_HOST: http://127.0.0.1:9
    steps:
      - uses: actions/checkout@v4

      - uses: astral-sh/setup-uv@v6
        with:
          version: "0.8.8"
          enable-cache: true
          cache-dependency-glob: backend/uv.lock

      - name: Install dependencies
        run: uv sync --locked

      - name: Unit tests
        run: uv run pytest

  docker:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build image
        run: docker build -t scholar-api backend

      - name: Image serves /health on $PORT with no other configuration
        run: |
          docker run -d --name api -e PORT=9090 -p 9090:9090 scholar-api
          for i in $(seq 1 30); do
            if curl -sf http://127.0.0.1:9090/health; then exit 0; fi
            sleep 2
          done
          docker logs api
          exit 1
```

- [ ] **Step 5: Update the docs**

In `README.md`, replace the code block under `### Environment Variables` (the one listing `EMBEDDING_MODEL`, `CHROMA_PERSIST_DIR`, ...; those variables do not exist) with:

````markdown
All settings are optional. With none set, Scholar runs fully locally on Ollama + ChromaDB.

| Variable | Default | Meaning |
|---|---|---|
| `LLM_PROVIDER` | `ollama` | `ollama` or `vertex` |
| `OLLAMA_LLM_MODEL` | `gpt-oss:20b` | Ollama chat model |
| `OLLAMA_EMBED_MODEL` | `nomic-embed-text` | Ollama embedding model |
| `VERTEX_LLM_MODEL` | none | required for `vertex`, e.g. a current Gemini Flash model from the [Vertex model list](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/model-versions) |
| `VERTEX_EMBED_MODEL` | none | required for `vertex`, e.g. `gemini-embedding-001` |
| `VERTEX_THINKING_BUDGET` | model default | optional thinking-token budget for Gemini |
| `GOOGLE_CLOUD_PROJECT` | none | required for `vertex` |
| `GOOGLE_CLOUD_LOCATION` | `us-central1` | Vertex region |
| `CHROMA_DIR` | `./chroma_db` | Chroma storage directory |
| `UPLOAD_DIR` | `uploads` | uploaded files and extracted text |
| `CORS_ORIGINS` | localhost:3000/3001, 127.0.0.1:3000/3001, `null` | comma separated; `*` is not allowed |

### Running with Vertex AI (Gemini) locally

```bash
gcloud auth application-default login          # Vertex uses ADC; never set GOOGLE_API_KEY / GEMINI_API_KEY
cd backend && uv sync --extra cloud
LLM_PROVIDER=vertex GOOGLE_CLOUD_PROJECT=your-project \
VERTEX_LLM_MODEL=<gemini model> VERTEX_EMBED_MODEL=gemini-embedding-001 \
CHROMA_DIR=./chroma_db_vertex uv run uvicorn app.main:app --reload
```

Use a separate `CHROMA_DIR` per provider: Vertex and Ollama embeddings have different
dimensions and must never share a collection.
````

In `backend/RAG_PIPELINE_README.md`, replace the "Required Packages" list with:

```markdown
### Required Packages
- `langchain>=1.4.5`
- `langchain-ollama>=1.1.0`
- `langchain-chroma>=1.0.0,<1.1` (ChromaDB integration)
- `chromadb==1.0.20` (pinned so existing local stores keep their on-disk format)
- `langchain-google-genai>=4.4.1` (optional `cloud` extra, for Vertex AI)
```

- [ ] **Step 6: Verify locally what can be verified without Docker**

```bash
uv run pytest -p no:cacheprovider -q 2>&1 | tail -1
cd .. && backend/.venv/bin/python -c "import yaml; d=yaml.safe_load(open('.github/workflows/backend.yml')); print(sorted(d['jobs']), d['permissions'])"
```
Expected: `81 passed, 3 deselected`, then `['docker', 'test'] {'contents': 'read'}`.

- [ ] **Step 7: Commit**

```bash
cd /Users/mj/github/personal/scholar
git add backend/pyproject.toml backend/uv.lock backend/Dockerfile backend/.dockerignore .github/workflows/backend.yml README.md backend/RAG_PIPELINE_README.md
git commit -m "Add container image, dev dependency group, CI docker job and config docs

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_018KkrpaKskjiWpMfynhy8W7"
```

- [ ] **Step 8: Push and verify both CI jobs (the push was approved for this branch)**

```bash
git push
export PATH=/opt/homebrew/bin:$PATH
sleep 20; gh run watch --exit-status $(gh run list --branch gcp-deployment --workflow backend --limit 1 --json databaseId -q '.[0].databaseId')
```
Expected: the `test` and `docker` jobs both succeed. This is the only verification that the image builds and serves `/health` on `$PORT`, because Docker is not installed locally.

---

## Manual verification for MJ (needs your Google Cloud credentials)

The agent cannot run these:

```bash
gcloud auth application-default login
cd backend && uv sync --extra cloud
LLM_PROVIDER=vertex GOOGLE_CLOUD_PROJECT=<project> VERTEX_LLM_MODEL=<gemini model> \
VERTEX_EMBED_MODEL=gemini-embedding-001 CHROMA_DIR=./chroma_db_vertex UPLOAD_DIR=./uploads_vertex \
uv run uvicorn app.main:app --port 8000
# then in the app: upload a PDF in Q&A mode, ask a question, generate a quiz, generate flashcards
```

## M2a acceptance checklist

- [ ] With no env vars: the suite is green, and only D12 changes output (its own labeled commit).
- [ ] The CI `test` and `docker` jobs are green. The image serves `/health` on `PORT=9090`.
- [ ] A plain `uv sync` does not install Google packages, and `import app.main` works without them.
- [ ] There are no `run_in_executor`, `OllamaLLM(` or `OllamaEmbeddings(` calls outside `app/core/providers.py`.
- [ ] MJ runs the Vertex flow above successfully (Q&A, quiz, flashcards).
