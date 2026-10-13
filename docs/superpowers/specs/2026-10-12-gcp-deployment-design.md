# Scholar: GCP deployment design

Date: 2026-10-12
Status: M1 and M2a designed and approved. M2b, M3 and M4 have requirements recorded here and get a short design pass before each one starts.

## Goal

Make the Scholar backend deployable to Cloud Run using Vertex AI (Gemini + Vertex embeddings), Cloud SQL Postgres with pgvector, and Cloud Storage. The current local mode (Ollama + ChromaDB + local disk) must keep working unchanged. Everything is selected by environment variables. With no env vars set, the app behaves exactly as it does today.

Scope: `backend/`, plus one change in `frontend/lib/api.ts` (the client id header). No frontend redesign, no Electron packaging changes.

## Fixed constraints

- Do not change prompts, chunking parameters (1,000 chars / 200 overlap), or API response shapes.
- Do not use Vertex AI Vector Search. Do not put ChromaDB or SQLite on a GCS mount.
- Do not remove local Ollama mode. Do not commit credentials or a filled-in `.env`.
- No Gemini API keys anywhere. Vertex is reached through ADC / the service account only.
- MJ does all manual GCP setup and deployment (gcloud, console, IAM, secrets). The agent only documents those steps in the README.

## Decisions

| # | Decision | Reason |
|---|---|---|
| D1 | One spec, five milestones in order: M1, M2a, M2b, M3, M4. Each can be merged separately with tests green. After M2b merges, **stop**: MJ deploys to Cloud Run before M3 starts. | Keeps diffs reviewable. M3 and M4 are verified against the live service. |
| D2 | Upgrade the langchain stack to 1.x. The cloud LLM is `langchain-google-genai` 4.x `ChatGoogleGenerativeAI(vertexai=True)`, not `ChatVertexAI`. | `ChatVertexAI` is deprecated. Current `langchain-google-vertexai`, `langchain-postgres` and `langchain-google-genai` all need langchain-core ≥1.1. |
| D3 | `VERTEX_LLM_MODEL` and `VERTEX_EMBED_MODEL` are required when `LLM_PROVIDER=vertex`, with no default. | `gemini-2.5-flash` retires on Vertex on 2026-10-20. A hardcoded default would go stale the same way. |
| D4 | Sessions (QA sessions, quizzes, quiz sessions) are persisted in Postgres in cloud mode, with in-memory as the local default. | They currently vanish on scale-to-zero and differ between Cloud Run instances. |
| D5 | Client isolation uses a request-scoped `ContextVar`, set by a FastAPI dependency and read by the stores (approach A). The stores fail closed. | Public service signatures stay unchanged, and M3 logging reuses the same context. |
| D6 | A `file_id` owned by another client returns the same 404 as a missing one. | Prevents probing for file ids. |
| D7 | Remove the duplicate embedding pass in `rag_pipeline` (in M2a). | Each chunk is embedded twice today, which doubles the Vertex embedding cost. The response shape is preserved. |
| D8 | Never use `loop.run_in_executor` for store or LLM calls. Use `ainvoke` or `asyncio.to_thread`, which copies the context. | `run_in_executor` does not propagate `ContextVar`s, which would break isolation and logging context. |
| D9 | Shared wiring: keep the existing one-singleton-per-module pattern, and make constructors default to that singleton instead of building new instances. No `container.py`. | Existing tests patch `app.services.<x>.llm_service` and construct services directly. This keeps them working unchanged. |
| D10 | The default `CORS_ORIGINS` adds `http://127.0.0.1:3000` and `http://127.0.0.1:3001`. A `*` entry is rejected at startup. | The packaged Electron app loads `http://127.0.0.1:3001` (`electron/main.js:177`), which today only gets through via the wildcard. |
| D11 | Leave `max_tokens` unset for Vertex (parity). Add an optional `VERTEX_THINKING_BUDGET` (unset = model default). | MJ wants to tune thinking per use case later. A 2048 cap would count thinking tokens and truncate answers. |
| D12 | `VectorStoreService` always returns `similarity_score` as a 0–1 relevance score where higher is better, on both backends. Done in M2a as its own commit, labeled as a bug fix that **changes local output**. | Existing bug: Chroma returns a distance (lower = better), but `qa_service` treats the value as relevance in `_source_match_percent`, the heuristic grounding check (`similarity * 0.5`), `_score_band`, evidence-ref scores and `_calculate_confidence_score`. |
| D13 | Cloud-mode cost guardrails: maximum upload size, maximum chunks per document, and a per-`client_id` rate limit on LLM-calling routes. They return 413, 413 and 429. Enforced only in cloud mode, so local behavior stays unchanged. | Bounds Vertex spend from a single client or file on a public URL. |
| D14 | In M4, groundedness is scored by the separate judge model, not the app's critic. Critic-vs-judge agreement on per-sentence support labels is reported as its own metric. | The critic shouldn't grade itself. The agreement number measures how much the in-app critic can be trusted. |
| D15 | `GOOGLE_CLOUD_LOCATION` defaults to `global`, not `us-central1`. | Verified 2026-10-12: gemini-3.x models return 404 from `us-central1` and work from `global`; gemini-embedding-001 works from `global` too. |

## Configuration (`app/core/config.py`)

A frozen `Settings` dataclass built from `os.environ` by a cached `get_settings()`. `validate()` collects every problem and raises one `ConfigError` listing them all. `app/main.py` calls it before building the app, so a bad config stops startup with a readable message.

| Var | Default | Milestone | Notes |
|---|---|---|---|
| `LLM_PROVIDER` | `ollama` | M2a | `ollama` or `vertex` |
| `OLLAMA_LLM_MODEL` | `gpt-oss:20b` | M2a | |
| `OLLAMA_EMBED_MODEL` | `nomic-embed-text` | M2a | |
| `VERTEX_LLM_MODEL` | none | M2a | required when vertex (D3) |
| `VERTEX_EMBED_MODEL` | none | M2a | required when vertex (D3) |
| `VERTEX_THINKING_BUDGET` | unset | M2a | optional int, passed only when set (D11) |
| `GOOGLE_CLOUD_PROJECT` | none | M2a | required when vertex |
| `GOOGLE_CLOUD_LOCATION` | `global` | M2a | Vertex model location (D15); independent of the Cloud Run region |
| `UPLOAD_DIR` | `uploads` | M2a | local storage |
| `CHROMA_DIR` | `./chroma_db` | M2a | chroma backend |
| `CORS_ORIGINS` | `http://localhost:3000,http://localhost:3001,http://127.0.0.1:3000,http://127.0.0.1:3001,null` | M2a | comma separated; `*` rejected (D10) |
| `VECTOR_BACKEND` | `chroma` | M2b | `chroma` or `pgvector` |
| `DATABASE_URL` | none | M2b | required when pgvector or postgres sessions; SQLAlchemy psycopg URL |
| `STORAGE_BACKEND` | `local` | M2b | `local` or `gcs` |
| `GCS_BUCKET` | none | M2b | required when gcs |
| `SESSION_BACKEND` | `memory` | M2b | `memory` or `postgres` |
| `MAX_UPLOAD_MB` | `20` | M2b | cloud mode; checked before extraction, returns 413 (D13) |
| `MAX_CHUNKS_PER_DOC` | `500` | M2b | cloud mode; checked after chunking, before embedding, returns 413 (D13). Default to be confirmed in the M2b design pass |
| `RATE_LIMIT_PER_MIN` | `20` | M2b | cloud mode; LLM calls per `client_id` per minute per instance, returns 429 (D13). Default to be confirmed in the M2b design pass |
| `ENABLE_TRACING` | `false` | M3 | |
| `PRICE_INPUT_PER_1M`, `PRICE_OUTPUT_PER_1M` | `0` | M3 | MJ fills these from the Vertex pricing page |

**Cloud mode** means at least one of: `LLM_PROVIDER=vertex`, `VECTOR_BACKEND=pgvector`, `STORAGE_BACKEND=gcs` or `SESSION_BACKEND=postgres`. It controls the `X-Client-Id` requirement (M2b).

**API-key guard:** if `LLM_PROVIDER=vertex` and `GOOGLE_API_KEY` or `GEMINI_API_KEY` is set, validation fails. Otherwise the google-genai SDK would silently switch from Vertex/ADC to API-key mode.

## M1: Foundation (zero behavior change)

**Commit 1, test harness (on the current 0.3 stack):**
- `backend/pytest.ini`: rename the `[tool:pytest]` header to `[pytest]` (pytest currently ignores the file). Add `asyncio_mode = auto`, register the `integration` marker, and add `-m "not integration"` to `addopts`.
- Add a module-level `pytestmark = pytest.mark.integration` to `app/tests/test_rag_llm.py` and `app/tests/test_simple_rag.py` (they need a running Ollama).
- Record the resulting pass/deselect counts as the baseline. Today, before the fix, the result is 37 passed and 4 failed (async tests never set up).

**Commit 2, upgrade:**
- Bump `langchain`, `langchain-chroma`, `langchain-ollama` and `langchain-community` to their 1.x-compatible lines (resolved on 2026-10-12: langchain 1.4.5, langchain-ollama 1.1.0, langchain-community 0.4.2, langchain-core 1.6.10; langchain-chroma pinned `>=1.0.0,<1.1` because 1.1.0 requires chromadb ≥1.3.5). Regenerate `uv.lock`.
- Pin `chromadb==1.0.20` in `pyproject.toml` (with `langchain-chroma<1.1`) so the on-disk format of existing `chroma_db/` data does not change.
- Code edits are limited to import paths, if any are needed. The app imports only `langchain_ollama` and `langchain_chroma`, which keep their paths.

**Commit 3, CI:** `.github/workflows/backend.yml` runs on every push. It installs uv, runs `uv sync --locked` in `backend/`, then `uv run pytest`.

**Acceptance:**
- The same tests pass before and after the upgrade. Test edits are limited to markers and import paths.
- Manual smoke test against real Ollama with the existing `chroma_db/`: upload, ask, quiz and flashcards behave the same as before.
- Known risk: langchain-ollama 1.x exposes a `reasoning` option, so gpt-oss output may include or drop thinking text. If the smoke test shows a difference, set `reasoning` explicitly to reproduce today's output.

## M2a: Config, providers, wiring, CORS, container

**`app/core/providers.py`:**
- `get_llm(temperature)` returns `OllamaLLM(model=OLLAMA_LLM_MODEL, temperature=…)`, or `ChatGoogleGenerativeAI(model=VERTEX_LLM_MODEL, project=…, location=…, vertexai=True, temperature=…, [thinking_budget=VERTEX_THINKING_BUDGET])`.
- `get_embeddings()` returns `OllamaEmbeddings(model=OLLAMA_EMBED_MODEL)` or `GoogleGenerativeAIEmbeddings(model=VERTEX_EMBED_MODEL, project=…, location=…, vertexai=True)`.
- Google imports happen only inside the vertex branches. Google packages live in an optional `cloud` extra, so a plain local `uv sync` does not install them.
- The plan verifies the exact constructor parameter names against the resolved langchain-google-genai version. Gemini 3 models prefer `thinking_level` over `thinking_budget`. If the chosen model rejects `thinking_budget`, the plan notes that and MJ decides.

**Services:**
- `LLMService.__init__` uses `get_llm(temperature)`. The default `model_name` comes from config for the active provider. `max_tokens` stays stored but unused (D11).
- `EmbeddingService.__init__` and `VectorStoreService.__init__` use `get_embeddings()`, and their default model names come from config. Chroma uses `CHROMA_DIR`.
- `LLMService._generate_response`:
  ```python
  response = await self.llm.ainvoke(prompt)
  text = response.text if isinstance(response, BaseMessage) else response
  return text.strip()
  ```
  `.text` joins only the text parts when genai returns `content` as a list of parts (thinking + text). No prompt text changes.

**Shared wiring (D9):**
- `document.py` gains a module-level `document_service = DocumentService()`.
- Every constructor that currently does `x or XService()` defaults to the shared module singleton instead: `QAService`, `QuizService`, `FlashcardService`, `RAGPipelineService` (document, embedding and vector store), and `routes/files.py`.
- Services keep referencing `llm_service` through their module global, so `patch('app.services.flashcard_service.llm_service', …)` still works.

**Duplicate embedding removal (D7):**
- `RAGPipelineService.process_document_upload` no longer calls `EmbeddingService.embed_batch`. The vector-store write embeds the chunks once.
- The response's `embedding` block keeps its keys. `total_embeddings` is the chunk count, and `successful_embeddings`/`failed_embeddings` come from the store write result (all on success, none on failure). `success` reflects whether embedding ran.

**Score normalization (D12), separate commit:**
- `VectorStoreService.search_similar` converts each backend's raw score to relevance = cosine similarity clamped to [0, 1]:
  - Chroma, the existing collection's default squared L2 on unit vectors: `clamp(1 - d/2)`.
  - PGVector, cosine distance: `clamp(1 - d)`.
- Callers and response shapes stay the same. Only the values change, so the commit message calls it a bug fix that changes local output (heatmap percentages, score bands, confidence).
- The plan verifies that Ollama `nomic-embed-text` and the Vertex embeddings return unit-length vectors. If either does not, Chroma relevance is computed from the cosine of the query and returned vectors instead of the L2 formula.
- Test: with a fake embedding store, a chunk closer to the query gets a strictly higher `similarity_score`, and every score is in [0, 1].

**CORS (D10):** `allow_origins` comes from `CORS_ORIGINS`. `allow_credentials=True` stays.

**Packaging:**
- `pyproject.toml`: `pyinstaller`, `pytest` and `pytest-asyncio` move to `[dependency-groups] dev`. uv installs that group by default, so local and Electron builds are unaffected. Add `[project.optional-dependencies] cloud = [langchain-google-genai, …]`. M2b and M3 extend this extra.
- `backend/Dockerfile`:
  - `python:3.13-slim`, with uv copied from a **pinned** `ghcr.io/astral-sh/uv:<version>` image.
  - `uv sync --frozen --no-dev --extra cloud`.
  - Runs as a non-root user.
  - `CMD` runs `.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}` via `sh -c`.
- `backend/.dockerignore`: `chroma_db/`, `uploads/`, `.venv/`, `__pycache__/`, `app/tests/`, `evals/results/`, `.env*`.
- CI gains a `docker build backend` step.

**Tests added:**
- Provider factory: the ollama branch, the vertex branch with the Google classes mocked, the thinking budget passed only when set, and the API-key guard.
- Config validation: missing vertex vars, a bad enum, wildcard CORS, and all problems reported together.
- `_generate_response` normalization: str, an AIMessage with string content, and an AIMessage with list-of-parts content.
- Shared wiring: every consumer holds the same `DocumentService`, `VectorStoreService` and `EmbeddingService` instance.
- Pipeline: the upload response keeps its shape, and the embedding service is not called.
- CORS: the default origins include `127.0.0.1:3001`.

**Acceptance:**
- No env vars: identical behavior. The M1 baseline tests still pass.
- With `LLM_PROVIDER=vertex`, both model vars, `GOOGLE_CLOUD_PROJECT` and local ADC, Q&A, quiz and flashcards work against a **fresh** `CHROMA_DIR`. Vertex and nomic vectors have different dimensions and must never share a collection.
- `docker build` succeeds, and the container answers `/health` on `$PORT`.

## M2b: Cloud backends and isolation (to be detailed before start)

Requirements from the brief, plus the decisions above:

- **Storage** (`app/services/storage.py`): `save_bytes`, `read_text`, `exists`, `delete`, `list_prefix`, with `LocalStorage` (`UPLOAD_DIR`) and `GCSStorage` (`GCS_BUCKET`). `DocumentService` stops using `Path`/`open()` for persisted files. Extraction may still use a request-local temp file. Keys are `{client_id}/{file_id}…`. `utils/file_utils.py` is currently empty. Blocking SDK calls run through `asyncio.to_thread` (D8).
- **pgvector:**
  - `PGVector(embeddings=get_embeddings(), collection_name="documents", connection=DATABASE_URL, use_jsonb=True)`.
  - Get-by-file and stats use SQLAlchemy over `langchain_pg_embedding` filtered on `cmetadata`. Delete uses `PGVector.delete(ids=…)`.
  - `VectorStoreService` public methods keep their signatures. Chroma is unchanged.
  - Add a comment that one collection must never mix embedding models.
  - Scores are normalized per D12, using the cosine-distance formula.
- **Sessions:**
  - A `SessionStore` interface, with an in-memory implementation (default) and a Postgres implementation: a `sessions` table with `id`, `client_id`, `kind` (qa/quiz/quiz_def), `data` JSONB, `created_at`, `updated_at`. Selected by `SESSION_BACKEND`.
  - All session CRUD in `qa_service` and `quiz_service` goes through it, scoped by `client_id`. That includes `active_quizzes`, so a quiz generated on one instance can be submitted on another.
  - The list endpoints return only the caller's sessions.
- **Isolation (D5, D6, D8):**
  - The `X-Client-Id` dependency is applied to all routers and validates a UUID. Cloud mode returns 400 when the header is missing. Local mode defaults to `"local"`.
  - `client_id` goes into chunk metadata at ingest. Every search, get and delete filters on `client_id` (plus `file_id` where applicable).
  - Add a TODO noting Firebase Auth or IAP as the next step.
- **Cost guardrails (D13, cloud mode only):**
  - Upload size is checked before extraction, and over `MAX_UPLOAD_MB` returns 413.
  - Chunk count is checked after chunking and before any embedding call, and over `MAX_CHUNKS_PER_DOC` returns 413. Nothing is stored for a rejected file.
  - Rate limit: an in-memory sliding window per `client_id` per instance on LLM-calling routes (QA ask/reflect, quiz generate/submit, flashcards generate, and upload with embedding). Over the limit returns 429 with `Retry-After`.
  - Tests cover each limit, and confirm local mode is unaffected.
- **Frontend:** `frontend/lib/api.ts` generates a UUID once, keeps it in `localStorage`, and sends `X-Client-Id` on every request, including `uploadFile`.
- **Tests:**
  - Storage interface (local implementation, GCS mocked).
  - Isolation through the HTTP layer: client A cannot search, read, or delete client B's file, and gets a 404 for it. One case exercises a code path that runs in a worker thread via `asyncio.to_thread`.
  - Session scoping.
- **README:** a "Deploying to Google Cloud" section with every env var and MJ's manual gcloud steps, documented only.
- **Then stop.** MJ deploys and verifies acceptance criteria 2–4 before M3.

## M3: Observability (to be detailed before start)

- Per LLM call, emit one JSON line to stdout containing: `request_id`, `client_id`, model, `input_tokens`, `output_tokens_visible`, `thinking_tokens`, `latency_ms`, `tokens_per_sec`, `est_cost_usd`.
  - Token counts come from `usage_metadata`. Ollama logs `None` where a count is unavailable.
  - Thinking tokens come from `usage_metadata.output_token_details.reasoning`.
  - Both **cost** and **tokens/sec** count thinking tokens as output, because they are billed as output. The plan verifies whether genai's `output_tokens` already includes reasoning, so they are not double-counted.
- Prices come from `PRICE_INPUT_PER_1M` / `PRICE_OUTPUT_PER_1M`.
- OpenTelemetry: FastAPI instrumentation plus manual `retrieve` and `generate` spans. Export to Cloud Trace only when `ENABLE_TRACING=true`; otherwise no-op.
- `GET /metrics/summary` returns per-process totals: calls, tokens (visible and thinking), average latency, and total estimated cost.

## M4: Evaluation harness (to be detailed before start)

- `backend/evals/`: 3–5 public documents committed to the repo, about 30 questions in versioned JSONL, each with an expected source location and a reference answer. The set is frozen and carries a version string.
- `uv run python -m evals.run --provider ollama|vertex` reports:
  - retrieval hit rate @k
  - groundedness, scored by the separate judge model, which labels each answer sentence's support (D14)
  - critic-vs-judge agreement: per-sentence agreement between the app's `audit_sentence_support_levels` labels and the judge's labels, reported as its own metric
  - LLM-as-judge correctness against the reference answer, using a separate fixed judge prompt and model
  - latency p50/p95, tokens/sec, and average cost per request (reusing M3)
- Results go to `evals/results/<timestamp>-<provider>.json` with the eval-set version and model names, and a summary table is printed. The runner is manual. Unit tests never call real cloud APIs.
- Expected sources are matched by page/text span, not chunk id, so the match does not depend on chunk-id formats.

## Acceptance criteria (whole project)

1. `uv run uvicorn app.main:app` with no env vars behaves exactly as before.
2. In cloud mode with valid credentials: upload a PDF, ask a question, generate a quiz, generate flashcards. All succeed.
3. Restarting the container loses nothing: files, embeddings and sessions all survive.
4. Two different `X-Client-Id` values cannot see each other's documents or sessions.
5. Every LLM call emits one JSON log line with tokens (visible and thinking), latency, tokens/sec and estimated cost.
6. `docker build` succeeds and the image serves on `$PORT`.
