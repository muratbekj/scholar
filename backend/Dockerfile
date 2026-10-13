FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:0.8.8 /uv /bin/uv

# UV_NO_CACHE keeps uv's download cache out of the image layer
ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_CACHE=1

WORKDIR /app
# Only /app itself must be writable (the app creates chroma_db/ and uploads/ there);
# the venv stays root-owned and is not rewritten into a second layer.
RUN useradd --create-home --uid 10001 app && chown app:app /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --extra cloud --no-install-project

COPY --chown=app:app app ./app
USER app

EXPOSE 8080
CMD ["sh", "-c", "exec /app/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
