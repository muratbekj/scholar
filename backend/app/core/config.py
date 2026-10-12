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
