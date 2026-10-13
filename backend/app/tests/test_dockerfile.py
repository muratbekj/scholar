"""Guards against Dockerfile patterns that duplicate the venv in the image (Docker isn't available locally)."""
from pathlib import Path

DOCKERFILE = (Path(__file__).resolve().parents[2] / "Dockerfile").read_text()


def test_uv_cache_is_not_kept_in_the_image():
    assert "UV_NO_CACHE=1" in DOCKERFILE


def test_no_recursive_chown_rewriting_the_venv_layer():
    assert "chown -R" not in DOCKERFILE


def test_app_code_is_copied_owned_by_the_runtime_user():
    assert "COPY --chown=app:app app ./app" in DOCKERFILE
    assert "USER app" in DOCKERFILE
