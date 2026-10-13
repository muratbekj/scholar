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
    assert s.google_cloud_location == "global"  # Gemini 3.x models are served only from global


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


# --- M2b: cloud backends, limits, cloud-extra check ---------------------------------

from app.core import config as config_mod
from app.core.config import missing_cloud_packages

DB = "postgresql+psycopg://u:p@h/db"


def test_cloud_backends_default_to_local():
    s = Settings.from_env({})
    assert (s.vector_backend, s.storage_backend, s.session_backend) == ("chroma", "local", "memory")
    assert s.cloud_mode is False
    assert (s.max_upload_mb, s.max_chunks_per_doc, s.rate_limit_per_min) == (20, 500, 20)


@pytest.mark.parametrize("env", [
    {"VECTOR_BACKEND": "pgvector", "DATABASE_URL": DB},
    {"STORAGE_BACKEND": "gcs", "GCS_BUCKET": "b"},
    {"SESSION_BACKEND": "postgres", "DATABASE_URL": DB},
    VERTEX_OK,
])
def test_any_cloud_backend_enables_cloud_mode(env):
    assert Settings.from_env(env).cloud_mode is True


def test_postgres_backends_require_database_url():
    with pytest.raises(ConfigError, match="DATABASE_URL"):
        Settings.from_env({"VECTOR_BACKEND": "pgvector", "SESSION_BACKEND": "postgres"})


def test_gcs_requires_bucket():
    with pytest.raises(ConfigError, match="GCS_BUCKET"):
        Settings.from_env({"STORAGE_BACKEND": "gcs"})


def test_unknown_backend_values_rejected():
    with pytest.raises(ConfigError) as exc:
        Settings.from_env({"VECTOR_BACKEND": "faiss", "STORAGE_BACKEND": "s3", "SESSION_BACKEND": "redis"})
    for name in ("VECTOR_BACKEND", "STORAGE_BACKEND", "SESSION_BACKEND"):
        assert name in str(exc.value)


@pytest.mark.parametrize("value", ["0", "-5", "abc"])
def test_limits_must_be_positive_integers(value):
    with pytest.raises(ConfigError, match="MAX_UPLOAD_MB"):
        Settings.from_env({"MAX_UPLOAD_MB": value})


def test_limits_parsed():
    s = Settings.from_env({"MAX_UPLOAD_MB": "5", "MAX_CHUNKS_PER_DOC": "50", "RATE_LIMIT_PER_MIN": "3"})
    assert (s.max_upload_mb, s.max_chunks_per_doc, s.rate_limit_per_min) == (5, 50, 3)


def test_separator_only_cors_is_config_error():
    with pytest.raises(ConfigError, match="CORS_ORIGINS"):
        Settings.from_env({"CORS_ORIGINS": " , ,"})


def test_missing_cloud_packages_reported_with_install_hint():
    s = Settings.from_env({**VERTEX_OK, "STORAGE_BACKEND": "gcs", "GCS_BUCKET": "b"})
    problems = missing_cloud_packages(s, module_available=lambda name: False)
    assert len(problems) == 1
    assert "uv sync --extra cloud" in problems[0]
    assert "google.cloud.storage" in problems[0] and "langchain_google_genai" in problems[0]


def test_local_settings_need_no_cloud_packages():
    assert missing_cloud_packages(Settings.from_env({}), module_available=lambda name: False) == []


def test_get_settings_fails_when_cloud_packages_missing(monkeypatch):
    monkeypatch.setenv("STORAGE_BACKEND", "gcs")
    monkeypatch.setenv("GCS_BUCKET", "b")
    monkeypatch.setattr(config_mod, "_module_available", lambda name: False)
    config_mod.get_settings.cache_clear()
    try:
        with pytest.raises(ConfigError, match="uv sync --extra cloud"):
            config_mod.get_settings()
    finally:
        monkeypatch.undo()
        config_mod.get_settings.cache_clear()
