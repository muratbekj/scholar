# Frontend tasks — reflective gate, gaps, audit visibility, oversight quizzes

Work derived from the Scholar “epistemic trust” pillars, **frontend-only**: UX, components, API integration, and tests. Backend must expose gated flows, segment-level audit metadata, and quiz modes (see `backend/tasks.md`).

---

## 1. Reflective Gate (human intuition before full answer)

**Goal:** After the user asks a question, show **scaffolded** context (per API), **blur or hide** the full AI reply until the user submits a short hypothesis/summary, then reveal the complete response.

- [x] **1.1** Update API client/types (e.g. `lib/api.ts`, hooks) for **pending** vs **complete** Q&A states and **reflection submit** calls.
- [x] **1.2** On `app/qa/page.tsx` (and related components), implement **gated UI**: loading/pending, cue display, reflection text field, submit → unlock transition.
- [x] **1.3** Apply **blur / placeholder** treatment for withheld answer content until unlock; avoid flashing full text before reflection succeeds.
- [x] **1.4** Clear error/retry states if reflection submission fails; preserve draft reflection where helpful.
- [x] **1.5** Accessibility: labels for the reflection step, keyboard flow, screen reader text explaining why the answer is gated.

---

## 2. Logic-Gap presentation (AfterMath — steps + gaps)

**Goal:** Render step-by-step content with explicit **[Gap]** (or equivalent) slots; collect learner input and show review feedback from the API.

- [x] **2.1** Components for **multi-step** display: steps list, gap inputs, submit for Q&A gap-mode responses (if exposed) and/or quiz items.
- [x] **2.2** Quiz page (`app/quiz/page.tsx`): mode selector or route for **reasoning-gap** items; render gap structure from API payload.
- [x] **2.3** Review UI after grading: show **why** an answer was accepted (rubric/explanation from backend).
- [x] **2.4** Mobile/desktop layout for long proofs (scroll, sticky actions).

---

## 3. Dual-Agent audit presentation (shortcut visibility)

**Goal:** Surface backend audit results: which parts of the answer are **grounded in the doc** vs **weak / filler**, reducing automation bias through visible structure.

- [x] **3.1** Render **segmented** assistant text from `answer_segments` (or equivalent) with per-segment styles/icons.
- [x] **3.2** Inline or panel UI for **evidence**: chunk excerpts, page references, jump-to-source if available.
- [x] **3.3** Optional **summary** strip: short audit summary from API for learners who want prose context.
- [x] **3.4** Do **not** infer grounding purely client-side from raw embeddings; trust backend tiers/scores.

---

## 4. Transparency heatmap (hover / provenance)

**Goal:** Color-coded or tier-coded text with **hover** (or tap) detail: “source match” or band label — green / yellow / red aligned with backend semantics.

- [x] **4.1** Map backend **support tier** (and optional score) to **theme colors** and legend copy (direct citation, inference, statistical filler).
- [x] **4.2** Tooltip/popover on hover/focus: show **percentage or band**, source excerpt, and chunk id/page if provided.
- [x] **4.3** Ensure contrast and color-blind-safe patterns (not color alone).
- [x] **4.4** Loading/empty states when audit metadata is partial (degrade gracefully to unstyled text + message).

---

## 5. Metacognitive “auditor” quizzes

**Goal:** UI for quiz items that show a **prior AI response** and ask the learner to spot issues, tied to PDF evidence; grading feedback emphasizes oversight skills.

- [x] **5.1** Quiz flow for **AI oversight** mode: display synthetic/stored AI claim, evidence panel, free-text or structured critique input.
- [x] **5.2** Post-submit **review** screen: what was strong in the learner’s critique, what evidence was missing, link to sources.
- [x] **5.3** Copy framing: position the learner as **auditor** (tone aligned with product ethics), without preachy walls of text.

---

## Verification (frontend)

- [ ] **V.1** Component/integration tests for gated Q&A, heatmap tooltips, and quiz mode rendering (align with project test runner).
- [ ] **V.2** Manual E2E: question → reflection → revealed answer with segments; complete one reasoning-gap and one oversight quiz.
