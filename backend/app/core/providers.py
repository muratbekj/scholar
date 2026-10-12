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
