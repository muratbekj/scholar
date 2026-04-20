# Backend tasks — mindful Q&A, audit, and quiz modes

Work derived from the Scholar “epistemic trust” pillars: **Reflective Gate**, **Logic-Gap (AfterMath)**, **Dual-Agent audit**, **transparency metadata** (for UI heatmap), and **metacognitive auditor quizzes**. Check items off as you implement.

---

## 1. Reflective Gate (delayed / gated answer)

**Goal:** Retrieve source context server-side, but do not return the full model answer until the learner has submitted a short hypothesis or summary (“human intuition”).

- [x] **1.1** Model a **two-stage Q&A contract**: e.g. “pending” response (cue + reflection prompt + retrieved evidence policy) vs “complete” response (full answer after reflection). Extend `app/models/qa.py` and `app/api/routes/qa.py` accordingly.
- [x] **1.2** In `app/services/qa_service.py`, after retrieval, return **scaffolded** content before reflection (e.g. one cue sentence or bounded cue text per product policy) and **withhold** the main generated answer until reflection is submitted.
- [x] **1.3** Add an endpoint or request phase for **submitting reflection** tied to a pending question (session/id), then run generation and return the final answer payload.
- [x] **1.4** (Optional) Classify **query complexity** and skip the gate for trivial prompts so friction matches pedagogical intent.
- [x] **1.5** Persist reflection text with the Q&A exchange if sessions/analytics should retain it (align with existing session models).

---

## 2. Logic-Gap generation (“Incomplete proofs” — Q&A + quiz)

**Goal:** For suitable content (math, code, logic), produce step-by-step structure with explicit **gaps** the learner must fill; backend owns generation and evaluation rules.

- [x] **2.1** Extend quiz (and Q&A if applicable) models in `app/models/quiz.py` / `app/models/qa.py` for **gap** structures: ordered steps, placeholders, acceptable rubric hints for grading.
- [x] **2.2** In `app/services/quiz_service.py`, add generation mode(s) for **reasoning-gap** items: constrained formats, evaluator metadata (equivalent reasoning, not only exact string match).
- [x] **2.3** In `app/services/qa_service.py` (or shared generation helper), support **gap-style** answers where the API returns structured steps + gaps instead of only flat prose when requested.
- [x] **2.4** Expose modes on `app/api/routes/quiz.py` (and Q&A routes if needed) via explicit **generation mode** enum or flags.
- [x] **2.5** Implement grading for gap submissions (LLM-as-judge or rubric + evidence) and return clear **review** payloads for the frontend.

---

## 3. Dual-Agent audit (“Critic” / shortcut detector)

**Goal:** After the primary answer, run an **audit** pass against retrieved document evidence that labels spans as document-grounded vs weakly supported / likely prior-knowledge filler (“guessing” vs “knowing” in product language).

- [x] **3.1** Add an **audit step** in the LangChain / generation pipeline (e.g. `qa_service`, `rag_pipeline`, or dedicated module): candidate answer + retrieved chunks → structured audit output.
- [x] **3.2** Define a stable schema for **segments** with labels (e.g. grounded / inferred / weak support — map to green / yellow / red in the UI) and **evidence references** (chunk ids, offsets, page hints).
- [x] **3.3** Implement the critic as a **second prompt** (or clearly separated chain step) on the **same** local stack, per capacity/latency constraints; avoid implying mathematical certainty where the model is heuristic.
- [x] **3.4** For **multi-turn** Q&A, pass a **bounded window** of prior turns (or summary) into the audit to catch propagated shortcuts.
- [x] **3.5** Attach **audit summary** text to responses for transparency copy (“what is well supported vs not”).

---

## 4. Transparency metadata for heatmap (RAG + audit)

**Goal:** Supply the client with **interpretable** grounding signals: retrieval similarity or tiered labels so the UI can show “source match” / hover detail without the frontend inventing scores.

- [x] **4.1** For each answer **segment** (or token span batch), include backend-derived fields: support **tier**, optional **retrieval score(s)**, and links to **source excerpts**.
- [x] **4.2** Normalize naming for UI: e.g. “direct citation,” “inference,” “weak / filler” aligned with audit labels; document in `API.md` if public.
- [x] **4.3** If exposing a **percentage**, define how it is computed from retrieval + audit (and avoid false precision; prefer bands if scores are soft).
- [x] **4.4** Ensure Q&A and quiz flows that return model text reuse the **same** segment/evidence shape where possible (shared Pydantic models / helpers).

---

## 5. Metacognitive “auditor” quizzes

**Goal:** Quiz mode that evaluates **critique of prior AI output** (missed details, shortcuts) using document evidence, not only PDF recall.

- [x] **5.1** Add quiz **mode** (e.g. `ai_oversight`) in models and `quiz_service`: build items from **stored or synthetic prior assistant claims** + cited evidence context.
- [x] **5.2** Grading: accept **any** valid evidence-backed critique (not a single canned “expected flaw”); prefer stronger scores when the learner cites **page / chunk / quote**.
- [x] **5.3** API: request/response shapes for oversight items, learner critique text, and **review** explanation after submit.
- [x] **5.4** Tests in `app/tests/` for generation shape, grading happy-path, and at least one edge case (wrong critique vs supported critique).

---

## Verification (backend)

- [x] **V.1** Extend or add pytest coverage for new routes, gated Q&A, audit payload shape, and new quiz modes.
- [x] **V.2** Confirm **backward compatibility** for existing clients: additive fields or transitional `answer` string if older UI still calls the API.
