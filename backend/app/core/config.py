"""Application settings read from environment variables.

With no environment variables set, the defaults reproduce the original fully
local setup: Ollama for the LLM and embeddings, Chroma on local disk.
"""
from __future__ import annotations

import base64
import importlib.util
import json
import os
import tempfile
from dataclasses import dataclass
from functools import lru_cache
from typing import Callable, List, Mapping, MutableMapping, Optional, Tuple

DEFAULT_CORS_ORIGINS: Tuple[str, ...] = (
    "http://localhost:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",  # packaged Electron app
    "null",  # Electron file:// requests
)
LLM_PROVIDERS = ("ollama", "vertex")
VECTOR_BACKENDS = ("chroma", "pgvector")
STORAGE_BACKENDS = ("local", "gcs")
SESSION_BACKENDS = ("memory", "postgres")
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
    google_cloud_location: str = "global"  # Gemini 3.x models are served only from global
    upload_dir: str = "uploads"
    chroma_dir: str = "./chroma_db"
    cors_origins: Tuple[str, ...] = DEFAULT_CORS_ORIGINS
    vector_backend: str = "chroma"
    database_url: Optional[str] = None
    storage_backend: str = "local"
    gcs_bucket: Optional[str] = None
    session_backend: str = "memory"
    max_upload_mb: int = 20
    max_chunks_per_doc: int = 500
    rate_limit_per_min: int = 20
    rate_limit_global_per_min: int = 100
    max_text_chars: int = 500_000

    @property
    def cloud_mode(self) -> bool:
        """True when any cloud backend is selected: X-Client-Id becomes required and data is isolated per client."""
        return (
            self.llm_provider == "vertex"
            or self.vector_backend == "pgvector"
            or self.storage_backend == "gcs"
            or self.session_backend == "postgres"
        )

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

        def choice(name: str, options: Tuple[str, ...], default: str) -> str:
            value = (get(name) or default).lower()
            if value not in options:
                problems.append(f"{name} must be one of {', '.join(options)}, got {value!r}")
            return value

        def positive_int(name: str, default: int) -> int:
            raw = get(name)
            if raw is None:
                return default
            try:
                value = int(raw)
            except ValueError:
                value = 0
            if value <= 0:
                problems.append(f"{name} must be a positive integer, got {raw!r}")
                return default
            return value

        provider = choice("LLM_PROVIDER", LLM_PROVIDERS, "ollama")
        vector_backend = choice("VECTOR_BACKEND", VECTOR_BACKENDS, "chroma")
        storage_backend = choice("STORAGE_BACKEND", STORAGE_BACKENDS, "local")
        session_backend = choice("SESSION_BACKEND", SESSION_BACKENDS, "memory")
        max_upload_mb = positive_int("MAX_UPLOAD_MB", cls.max_upload_mb)
        max_chunks_per_doc = positive_int("MAX_CHUNKS_PER_DOC", cls.max_chunks_per_doc)
        rate_limit_per_min = positive_int("RATE_LIMIT_PER_MIN", cls.rate_limit_per_min)
        rate_limit_global_per_min = positive_int("RATE_LIMIT_GLOBAL_PER_MIN", cls.rate_limit_global_per_min)
        max_text_chars = positive_int("MAX_TEXT_CHARS", cls.max_text_chars)

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
            if not cors_origins:
                problems.append("CORS_ORIGINS is set but lists no origins")

        # Browsers send Origin without a trailing slash, so a pasted "https://app.example/" would never match.
        frontend_url = (get("FRONTEND_URL") or "").rstrip("/")
        if frontend_url:
            if not frontend_url.startswith(("http://", "https://")):
                problems.append(f"FRONTEND_URL must start with http:// or https://, got {frontend_url!r}")
            elif frontend_url not in cors_origins:
                cors_origins += (frontend_url,)

        if (vector_backend == "pgvector" or session_backend == "postgres") and get("DATABASE_URL") is None:
            problems.append("DATABASE_URL is required when VECTOR_BACKEND=pgvector or SESSION_BACKEND=postgres")
        if storage_backend == "gcs" and get("GCS_BUCKET") is None:
            problems.append("GCS_BUCKET is required when STORAGE_BACKEND=gcs")

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
            vector_backend=vector_backend,
            database_url=_with_psycopg_driver(get("DATABASE_URL")),
            storage_backend=storage_backend,
            gcs_bucket=get("GCS_BUCKET"),
            session_backend=session_backend,
            max_upload_mb=max_upload_mb,
            max_chunks_per_doc=max_chunks_per_doc,
            rate_limit_per_min=rate_limit_per_min,
            rate_limit_global_per_min=rate_limit_global_per_min,
            max_text_chars=max_text_chars,
        )


def _with_psycopg_driver(url: Optional[str]) -> Optional[str]:
    """Hosted Postgres (e.g. Railway) hands out postgresql:// URLs; SQLAlchemy needs the psycopg 3 driver named."""
    if url is None:
        return None
    for scheme in ("postgresql://", "postgres://"):
        if url.startswith(scheme):
            return "postgresql+psycopg://" + url[len(scheme):]
    return url


def _decode_credentials(raw: str) -> str:
    """Accept the key file as JSON (optionally wrapped in quotes) or base64-encoded JSON."""
    candidates = [raw]
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in "'\"":
        candidates.append(raw[1:-1].strip())
    if not raw.startswith("{"):
        try:
            candidates.append(base64.b64decode(raw, validate=True).decode("utf-8").strip())
        except (ValueError, UnicodeDecodeError):
            pass
    for candidate in candidates:
        try:
            json.loads(candidate)
            return candidate
        except ValueError:
            continue
    # Describe the value without echoing any of it: it is a secret.
    try:
        json.loads(raw)
        detail = ""
    except ValueError as exc:
        detail = f"; JSON error at line {exc.lineno} column {exc.colno}"
    first = raw[0] if raw[0] in "{['\"" else "?"
    raise ConfigError(
        "Invalid configuration:\n  - GOOGLE_CREDENTIALS_JSON is not valid JSON or base64-encoded JSON "
        f"(got {len(raw)} characters, starts with '{first}'{detail}). Paste the whole key file as one line "
        "via the variable form, or base64-encode it."
    )


def apply_credentials_env(env: MutableMapping[str, str] = os.environ, directory: Optional[str] = None) -> None:
    """Hosts without Google's metadata server (e.g. Railway) pass a service-account key as
    GOOGLE_CREDENTIALS_JSON; write it to a private file and point Application Default Credentials at it."""
    raw = (env.get("GOOGLE_CREDENTIALS_JSON") or "").strip()
    if not raw or env.get("GOOGLE_APPLICATION_CREDENTIALS"):
        return
    raw = _decode_credentials(raw)
    fd, path = tempfile.mkstemp(prefix="gcp-credentials-", suffix=".json", dir=directory)
    with os.fdopen(fd, "w") as f:  # mkstemp creates the file with mode 0600
        f.write(raw)
    env["GOOGLE_APPLICATION_CREDENTIALS"] = path


def _module_available(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except ModuleNotFoundError:  # a parent package (e.g. "google") is missing
        return False


def missing_cloud_packages(
    settings: Settings, module_available: Optional[Callable[[str], bool]] = None
) -> List[str]:
    """Problems for selected cloud backends whose packages (the `cloud` extra) aren't installed."""
    available = module_available or _module_available
    needed: List[str] = []
    if settings.llm_provider == "vertex":
        needed.append("langchain_google_genai")
    if settings.vector_backend == "pgvector":
        needed += ["langchain_postgres", "psycopg"]
    if settings.session_backend == "postgres":
        needed.append("psycopg")
    if settings.storage_backend == "gcs":
        needed.append("google.cloud.storage")
    missing = sorted({name for name in needed if not available(name)})
    if not missing:
        return []
    return [f"missing packages {', '.join(missing)}: install the cloud extra with `uv sync --extra cloud`"]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Settings for this process, read from os.environ once. Raises ConfigError."""
    settings = Settings.from_env(os.environ)
    problems = missing_cloud_packages(settings)
    if problems:
        raise ConfigError("Invalid configuration:\n" + "\n".join(f"  - {p}" for p in problems))
    return settings
