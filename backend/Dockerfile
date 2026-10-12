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
