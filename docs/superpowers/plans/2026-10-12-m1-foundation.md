# M1 Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Put the backend on the langchain 1.x stack with a trustworthy, CI-enforced test suite, and change no app behavior.

**Architecture:** Three commits. (1) Fix the pytest config so async tests run and the Ollama-dependent tests are opt-in, then record a baseline. (2) Upgrade the langchain packages and regenerate the lock, keeping `chromadb` at 1.0.20 so the on-disk Chroma format does not change, then prove the results match the baseline and that existing Chroma data reads back the same. (3) Add a GitHub Actions workflow that runs the unit tests.

**Tech Stack:** Python 3.13, uv 0.8.8, pytest 8 + pytest-asyncio 1.x, langchain 1.4 / langchain-core 1.6, langchain-ollama 1.1, langchain-chroma 1.0, chromadb 1.0.20, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-10-12-gcp-deployment-design.md` (section "M1: Foundation", decisions D1 and D2)

## Global Constraints

- M1 makes zero behavior changes. No edits under `backend/app/` except test markers, plus import paths if the upgrade requires them.
- Test edits are limited to markers and import paths.
- Do not change prompts, chunking parameters (1,000 chars / 200 overlap), or API response shapes.
- `chromadb` stays at **1.0.20** in `uv.lock`. Because of that, `langchain-chroma` is pinned `>=1.0.0,<1.1` (1.1.0 requires `chromadb>=1.3.5`; resolved 2026-10-12). The version is held by `chromadb==1.0.20` in `pyproject.toml` (added after the final review): the `langchain-chroma` cap alone does not block `uv lock --upgrade` from moving chromadb.
- Do not touch Electron packaging. Electron starts the backend with `python -m uvicorn app.main:app`, so nothing changes there.
- Do not commit credentials, `.env` files, `chroma_db/` or `uploads/` (already in `backend/.gitignore`).
- All commands run from `backend/` unless stated otherwise.
- Commit messages end with `Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>`.
- `M1_DIR` is a scratch directory **outside the repo** used for the baseline and smoke outputs (this session's scratchpad: `/private/tmp/claude-501/-Users-mj-github-personal-scholar/f53fb526-00cc-4d20-9f80-1ed54cfa9caf/scratchpad/m1`). Shell variables do not persist between commands, so every command that uses `M1_DIR` sets it inline.

## Review Focus

1. **Existing Chroma data after the upgrade:** a collection written by the 0.3 stack must open under 1.x and return the same chunk ids and scores for the same query. Covered by the `search` comparison in Task 2 Step 4 and Task 3 Step 6.
2. **gpt-oss output format:** langchain-ollama 1.x must not start or stop including thinking text in answers. `reasoning` defaults to `None` in both 0.3.7 and 1.x, so the risk is low. Covered by the `has_think_tags` check in the smoke script.
3. **Clean checkout in CI:** no `chroma_db/`, no `uploads/`, no Ollama server. Module import still creates the Chroma store, and the tests must still pass. Covered by Task 4 Step 2 (fresh clone, Ollama pointed at a closed port).
4. **Stale lock:** `uv sync --locked` must fail if `pyproject.toml` and `uv.lock` disagree. Covered by Task 4's CI using `--locked` and the Task 3 Step 3 check.
5. **The integration marker can't silently hide unit tests:** only `test_simple_rag.py` and `test_rag_llm.py` may be deselected. Covered by the deselected-count assertion in Task 1 Step 5.

---

### Task 1: Make the pytest config effective and record the baseline

**Files:**
- Modify: `backend/pytest.ini` (whole file, 7 lines)
- Modify: `backend/app/tests/test_simple_rag.py` (add a marker after the imports)
- Modify: `backend/app/tests/test_rag_llm.py` (add a marker after the imports)

**Interfaces:**
- Consumes: nothing.
- Produces: the `integration` marker; `$M1_DIR/baseline-0.3.txt` (the pass list used by Task 3).

**Background:** `pytest.ini` uses the `[tool:pytest]` header, which only works in `setup.cfg`, so pytest ignores the file. As a result, async tests without an explicit `@pytest.mark.asyncio` (`test_extraction.py`, `test_simple_rag.py`) fail with "async def functions are not natively supported". `test_simple_rag.py` talks to a live Ollama (it swallows connection errors, so it "passes" without one). `test_rag_llm.py` defines no `test_*` functions today. Mark it anyway so any future test there is opt-in.

- [ ] **Step 1: Record the current (broken) state**

```bash
M1_DIR=/private/tmp/claude-501/-Users-mj-github-personal-scholar/f53fb526-00cc-4d20-9f80-1ed54cfa9caf/scratchpad/m1; mkdir -p "$M1_DIR"
uv run pytest -p no:cacheprovider -q 2>&1 | tail -6 | tee "$M1_DIR/before-ini-fix.txt"
```
Expected: `4 failed, 37 passed`. The failures are `test_extraction.py::test_text_extraction` and the three `test_simple_rag.py` tests, all with "async def functions are not natively supported".

- [ ] **Step 2: Replace `backend/pytest.ini`**

```ini
[pytest]
testpaths = app/tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short -m "not integration"
pythonpath = .
asyncio_mode = auto
markers =
    integration: needs a running Ollama with the models pulled; run with -m integration
```

- [ ] **Step 3: Mark the Ollama-dependent modules**

In `backend/app/tests/test_simple_rag.py`, add `import pytest` to the imports block (lines 5-8), then directly after the imports and before the first `def`:

```python
pytestmark = pytest.mark.integration
```

In `backend/app/tests/test_rag_llm.py`, add `import pytest` to the imports block (lines 5-6), then directly after the imports:

```python
pytestmark = pytest.mark.integration
```

Make no other edits to either file.

- [ ] **Step 4: Run the unit suite**

```bash
uv run pytest -p no:cacheprovider -q 2>&1 | tail -4
```
Expected: `38 passed, 3 deselected`. `test_extraction.py::test_text_extraction` now passes because of `asyncio_mode = auto`.

- [ ] **Step 5: Confirm the marker selects exactly the integration tests**

```bash
uv run pytest -p no:cacheprovider -q -m integration --collect-only 2>&1 | grep "::" 
```
Expected: exactly three lines, all in `app/tests/test_simple_rag.py` (`test_rag_components`, `test_full_pipeline`, `test_ollama_connection`). Any other file listed is a bug. Fix the marker placement.

- [ ] **Step 6: Save the baseline pass list**

```bash
M1_DIR=/private/tmp/claude-501/-Users-mj-github-personal-scholar/f53fb526-00cc-4d20-9f80-1ed54cfa9caf/scratchpad/m1
uv run pytest -p no:cacheprovider -q -rA 2>&1 | grep -E "^(PASSED|FAILED|ERROR|SKIPPED)" | sort > "$M1_DIR/baseline-0.3.txt"
wc -l "$M1_DIR/baseline-0.3.txt"
```
Expected: `38` lines, all `PASSED`.

- [ ] **Step 7: Commit**

```bash
git add pytest.ini app/tests/test_simple_rag.py app/tests/test_rag_llm.py
git commit -m "Fix pytest config and mark Ollama tests as integration

pytest.ini used the setup.cfg-only [tool:pytest] header, so pytest
ignored it and async tests without explicit markers never ran.
Enable asyncio auto mode and make the live-Ollama tests opt-in
with -m integration.

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: Capture the pre-upgrade smoke baseline against real Ollama

**Files:**
- Create (outside the repo): `$M1_DIR/smoke.py`
- Outputs (outside the repo): `$M1_DIR/smoke-before.json`, `$M1_DIR/smoke-env/` (isolated `CHROMA` and `uploads` data)

**Interfaces:**
- Consumes: the running app on the 0.3 stack (Task 1 commit).
- Produces: `$M1_DIR/smoke-before.json` with key `file_id`, used by Task 3 Step 6 as `--reuse-file-id`.

**Manual prerequisite (MJ):** Ollama is running, but `ollama list` shows **no models** on this machine. The smoke test needs:
```bash
ollama pull gpt-oss:20b        # ~13 GB
ollama pull nomic-embed-text   # ~270 MB
```
The executor stops here and asks MJ to run these. It does not pull 13 GB on its own.

**Why an isolated working copy:** the app writes `./chroma_db` and `./uploads` relative to the working directory. The smoke server runs from a copy of `backend/` (without `.venv`) in `$M1_DIR/smoke-env`, so MJ's real `chroma_db/` and `uploads/` are never touched. The same copy, with the same Chroma data, is reused after the upgrade. That is the "existing chroma_db" compatibility check.

- [ ] **Step 1: Write the smoke script**

Create `$M1_DIR/smoke.py`:

```python
"""M1 smoke test: run the real API flow and record comparable facts.

Usage:
  python smoke.py --out before.json
  python smoke.py --out after.json --reuse-file-id <id from before.json>
"""
import argparse
import json
import sys

import httpx

BASE = "http://127.0.0.1:8000"
QUERY = "What do chloroplasts use to convert light energy?"

# Fixed text, > 5000 chars so the document gets chunked.
PARAGRAPHS = [
    "Photosynthesis is the process by which green plants, algae and some bacteria convert light energy into chemical energy. "
    "It takes place mainly in the chloroplasts of leaf cells, which contain the pigment chlorophyll.",
    "The light-dependent reactions occur in the thylakoid membranes. Chlorophyll absorbs light, water is split, oxygen is "
    "released, and the energy carriers ATP and NADPH are produced.",
    "The Calvin cycle takes place in the stroma. Using ATP and NADPH, the enzyme RuBisCO fixes carbon dioxide into "
    "three-carbon sugars that the plant later turns into glucose and starch.",
    "Factors that limit the rate of photosynthesis include light intensity, carbon dioxide concentration and temperature. "
    "At low light intensity, increasing light raises the rate until another factor becomes limiting.",
    "Cellular respiration is the reverse process in many respects: glucose is broken down in the mitochondria to release "
    "energy as ATP, consuming oxygen and producing carbon dioxide and water.",
]
DOC = "\n\n".join(f"Section {i + 1}. " + PARAGRAPHS[i % len(PARAGRAPHS)] for i in range(30))


def search_facts(client: httpx.Client, file_id: str) -> list:
    r = client.get(f"{BASE}/files/search", params={"query": QUERY, "k": 5, "file_id": file_id})
    r.raise_for_status()
    return [
        {"id": x["id"], "text": x["content"][:80], "score": round(x["similarity_score"], 6)}
        for x in r.json()["results"]
    ]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--reuse-file-id")
    args = ap.parse_args()

    facts: dict = {}
    with httpx.Client(timeout=900) as client:
        # 1. Upload (QA mode -> chunk + embed + store).
        r = client.post(
            f"{BASE}/files/upload",
            params={"study_mode": "qa"},
            files={"file": ("photosynthesis.txt", DOC.encode(), "text/plain")},
        )
        facts["upload_status"] = r.status_code
        up = r.json()
        facts["upload_keys"] = sorted(up)
        facts["upload_rag"] = {
            "total_chunks": up["rag_processing"]["chunking"]["total_chunks"],
            "embedding": up["rag_processing"]["embedding"],
            "documents_stored": up["rag_processing"]["vector_storage"]["documents_stored"],
        }
        new_file_id = up["file_id"]
        facts["file_id"] = new_file_id

        # 2. Search: the new upload, plus (after upgrade) the file written by the old stack.
        facts["search_new"] = search_facts(client, new_file_id)
        if args.reuse_file_id:
            facts["search_reused"] = search_facts(client, args.reuse_file_id)

        # 3. Ask (may come back gated as pending; record state, not text).
        r = client.post(
            f"{BASE}/qa/ask",
            json={"question": QUERY, "file_id": new_file_id, "filename": "photosynthesis.txt"},
        )
        facts["ask_status"] = r.status_code
        ask = r.json()
        facts["ask_keys"] = sorted(ask)
        text = json.dumps(ask)
        facts["has_think_tags"] = "<think>" in text or "<|channel|>" in text

        # 4. Quiz.
        r = client.post(
            f"{BASE}/quiz/generate",
            json={"file_id": new_file_id, "filename": "photosynthesis.txt", "num_questions": 3},
        )
        facts["quiz_status"] = r.status_code
        facts["quiz_keys"] = sorted(r.json())

        # 5. Flashcards.
        r = client.post(
            f"{BASE}/flashcards/generate",
            json={"file_id": new_file_id, "filename": "photosynthesis.txt"},
        )
        facts["flashcards_status"] = r.status_code
        facts["flashcards_keys"] = sorted(r.json())

    with open(args.out, "w") as f:
        json.dump(facts, f, indent=2, sort_keys=True)
    print(json.dumps(facts, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Create the isolated working copy**

```bash
M1_DIR=/private/tmp/claude-501/-Users-mj-github-personal-scholar/f53fb526-00cc-4d20-9f80-1ed54cfa9caf/scratchpad/m1
rm -rf "$M1_DIR/smoke-env" && mkdir -p "$M1_DIR/smoke-env"
rsync -a --exclude .venv --exclude chroma_db --exclude uploads --exclude __pycache__ ./ "$M1_DIR/smoke-env/"
```

- [ ] **Step 3: Start the server on the 0.3 stack from the copy**

Run in the background (Bash `run_in_background: true`):
```bash
M1_DIR=/private/tmp/claude-501/-Users-mj-github-personal-scholar/f53fb526-00cc-4d20-9f80-1ed54cfa9caf/scratchpad/m1
cd "$M1_DIR/smoke-env" && UV_PROJECT_ENVIRONMENT=/Users/mj/github/personal/scholar/backend/.venv uv run --frozen uvicorn app.main:app --host 127.0.0.1 --port 8000
```
Wait until `curl -sf http://127.0.0.1:8000/health` returns `{"status":"healthy",...}`.

- [ ] **Step 4: Run the smoke script**

```bash
M1_DIR=/private/tmp/claude-501/-Users-mj-github-personal-scholar/f53fb526-00cc-4d20-9f80-1ed54cfa9caf/scratchpad/m1
uv run python "$M1_DIR/smoke.py" --out "$M1_DIR/smoke-before.json"
```
Expected: every `*_status` is `200`, `search_new` has 5 entries, and `has_think_tags` is `false`. If any status is not 200 on the **old** stack, stop and report: that is a pre-existing problem, and M1 must not hide it.

- [ ] **Step 5: Stop the server**

Stop the background uvicorn process. Keep `$M1_DIR/smoke-env/chroma_db` and `$M1_DIR/smoke-env/uploads`: Task 3 reuses them.

(No commit in this task. Nothing in the repo changes.)

---

### Task 3: Upgrade the langchain stack to 1.x

**Files:**
- Modify: `backend/pyproject.toml:7-22` (dependency bounds)
- Modify: `backend/uv.lock` (regenerated)
- Modify (only if an import breaks): files under `backend/app/` (import lines only)

**Interfaces:**
- Consumes: `$M1_DIR/baseline-0.3.txt` (Task 1), `$M1_DIR/smoke-before.json` and `$M1_DIR/smoke-env/` (Task 2).
- Produces: a lockfile on langchain-core 1.6.x that M2a builds on.

- [ ] **Step 1: Update the dependency bounds**

In `backend/pyproject.toml`, change exactly these four lines in `dependencies` and leave the rest unchanged:

```toml
    "langchain>=1.4.5",
    "langchain-chroma>=1.0.0,<1.1",
    "langchain-community>=0.4.2",
    "langchain-ollama>=1.1.0",
```

`chromadb>=1.0.20` stays as it is. The `<1.1` cap on `langchain-chroma` is what keeps chromadb at 1.0.20 (see Global Constraints).

- [ ] **Step 2: Regenerate the lock**

```bash
uv lock
```
`uv lock` keeps existing locked versions unless the new bounds force a change, so unrelated packages stay where they are.

- [ ] **Step 3: Verify the locked versions**

```bash
for p in langchain langchain-core langchain-chroma langchain-ollama langchain-community chromadb; do
  printf "%-22s" "$p"; grep -A1 "^name = \"$p\"$" uv.lock | grep version
done
uv lock --check && echo "lock consistent"
```
Expected:
```
langchain             version = "1.4.5"
langchain-core        version = "1.6.10"   (any 1.6.x)
langchain-chroma      version = "1.0.0"
langchain-ollama      version = "1.1.0"
langchain-community   version = "0.4.2"
chromadb              version = "1.0.20"
lock consistent
```
If `chromadb` is anything other than `1.0.20`, stop. Do not proceed with a Chroma format change.

- [ ] **Step 4: Sync and check the imports**

```bash
uv sync --locked
uv run python -c "import app.main; print('import ok')"
```
Expected: `import ok`. If an `ImportError` names a moved langchain module, fix that import line only (for example `langchain.text_splitter` → `langchain_text_splitters`). Today the app imports only `langchain_ollama` and `langchain_chroma`, which keep their paths in 1.x, so no change is expected.

- [ ] **Step 5: Compare the unit tests against the baseline**

```bash
M1_DIR=/private/tmp/claude-501/-Users-mj-github-personal-scholar/f53fb526-00cc-4d20-9f80-1ed54cfa9caf/scratchpad/m1
uv run pytest -p no:cacheprovider -q -rA 2>&1 | grep -E "^(PASSED|FAILED|ERROR|SKIPPED)" | sort > "$M1_DIR/after-1x.txt"
diff "$M1_DIR/baseline-0.3.txt" "$M1_DIR/after-1x.txt" && echo "IDENTICAL"
```
Expected: `IDENTICAL` (38 PASSED). Any difference fails M1's acceptance. Fix with import-path changes only, or stop and report.

- [ ] **Step 6: Run the smoke test on the 1.x stack against the old Chroma data**

Copy the lock and pyproject into the smoke copy (the copy keeps its `chroma_db/` and `uploads/` from Task 2), then start the server in the background:
```bash
M1_DIR=/private/tmp/claude-501/-Users-mj-github-personal-scholar/f53fb526-00cc-4d20-9f80-1ed54cfa9caf/scratchpad/m1
cp pyproject.toml uv.lock "$M1_DIR/smoke-env/"
cd "$M1_DIR/smoke-env" && UV_PROJECT_ENVIRONMENT=/Users/mj/github/personal/scholar/backend/.venv uv run --frozen uvicorn app.main:app --host 127.0.0.1 --port 8000
```
Once `/health` responds:
```bash
M1_DIR=/private/tmp/claude-501/-Users-mj-github-personal-scholar/f53fb526-00cc-4d20-9f80-1ed54cfa9caf/scratchpad/m1
FID=$(uv run python -c "import json;print(json.load(open('$M1_DIR/smoke-before.json'))['file_id'])")
uv run python "$M1_DIR/smoke.py" --out "$M1_DIR/smoke-after.json" --reuse-file-id "$FID"
```
Then stop the server.

- [ ] **Step 7: Compare the before and after smoke results**

```bash
M1_DIR=/private/tmp/claude-501/-Users-mj-github-personal-scholar/f53fb526-00cc-4d20-9f80-1ed54cfa9caf/scratchpad/m1
uv run python - "$M1_DIR/smoke-before.json" "$M1_DIR/smoke-after.json" <<'EOF'
import json, sys
b, a = (json.load(open(p)) for p in sys.argv[1:3])
problems = []
for k in ["upload_status", "upload_keys", "upload_rag", "ask_status", "ask_keys",
          "quiz_status", "quiz_keys", "flashcards_status", "flashcards_keys", "has_think_tags"]:
    if b[k] != a[k]:
        problems.append(f"{k}: before={b[k]!r} after={a[k]!r}")
# Chunk ids are random UUIDs per upload, so compare a fresh upload by text and score.
if [(x["text"], x["score"]) for x in b["search_new"]] != [(x["text"], x["score"]) for x in a["search_new"]]:
    problems.append("fresh upload: retrieved chunks or scores differ")
# The reused file is the same stored data, so its ids must match exactly.
if [x["id"] for x in a["search_reused"]] != [x["id"] for x in b["search_new"]]:
    problems.append("old Chroma data returns different chunks under 1.x")
for x, y in zip(b["search_new"], a["search_reused"]):
    if abs(x["score"] - y["score"]) > 1e-4:
        problems.append(f"score drift on {x['id']}: {x['score']} -> {y['score']}")
print("\n".join(problems) or "SMOKE IDENTICAL")
sys.exit(1 if problems else 0)
EOF
```
Expected: `SMOKE IDENTICAL`. If `has_think_tags` flipped to `true`, set `reasoning=False` explicitly on `OllamaLLM` in `app/services/llm_service.py`. That is the one allowed non-import code change, and only if this check fails. Re-run Steps 6-7 and note it in the commit message.

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml uv.lock
# plus any import-only fixes under app/, if Step 4 needed them
git commit -m "Upgrade langchain stack to 1.x

langchain 1.4.5, langchain-core 1.6.x, langchain-ollama 1.1.0,
langchain-community 0.4.2. langchain-chroma is capped below 1.1 so
chromadb stays at 1.0.20 and the on-disk Chroma format is unchanged.

No behavior change: the unit test pass list is identical to the
0.3 baseline, and a live Ollama smoke run (upload, search, ask,
quiz, flashcards) matches, including search over Chroma data
written by the 0.3 stack.

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: GitHub Actions CI for the backend unit tests

**Files:**
- Create: `.github/workflows/backend.yml` (repo root)

**Interfaces:**
- Consumes: `backend/pytest.ini` defaults (integration tests deselected), `backend/uv.lock`.
- Produces: the `backend` workflow, with one job `test` that M2a extends with a `docker build` step.

- [ ] **Step 1: Write the workflow**

```yaml
name: backend

on:
  push:
  pull_request:

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
```

- [ ] **Step 2: Reproduce CI locally from a clean clone**

This catches anything that only works because of local state (`.venv`, `chroma_db/`, `uploads/`, a running Ollama):
```bash
M1_DIR=/private/tmp/claude-501/-Users-mj-github-personal-scholar/f53fb526-00cc-4d20-9f80-1ed54cfa9caf/scratchpad/m1
rm -rf "$M1_DIR/ci-clone" && git clone -q /Users/mj/github/personal/scholar "$M1_DIR/ci-clone"
cd "$M1_DIR/ci-clone/backend" && OLLAMA_HOST=http://127.0.0.1:9 uv sync --locked && OLLAMA_HOST=http://127.0.0.1:9 uv run pytest -q 2>&1 | tail -3
```
Expected: `38 passed, 3 deselected`, with no `chroma_db`/`uploads` present beforehand. (Clone after Task 3's commit so the clone has the upgraded lock. Step 3 commits the workflow file itself, which doesn't affect this run.)

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/backend.yml
git commit -m "Add backend CI workflow running unit tests

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

- [ ] **Step 4: Verify on GitHub (needs MJ's go-ahead to push)**

Pushing is outward-facing, so ask MJ first. With approval:
```bash
git push -u origin gcp-deployment
gh run watch --exit-status $(gh run list --branch gcp-deployment --workflow backend --limit 1 --json databaseId -q '.[0].databaseId')
```
Expected: the `test` job passes.

---

## M1 acceptance checklist

- [ ] Task 1: `38 passed, 3 deselected`. Only `test_simple_rag.py` is deselected.
- [ ] Task 3 Step 3: `chromadb` is 1.0.20, and langchain-core is 1.6.x.
- [ ] Task 3 Step 5: the pass list is `IDENTICAL` to the 0.3 baseline.
- [ ] Task 3 Step 7: `SMOKE IDENTICAL`, including old Chroma data read under 1.x.
- [ ] Task 4 Step 2: a clean clone passes with no Ollama.
- [ ] Test edits are limited to `pytestmark` lines and `import pytest`.
