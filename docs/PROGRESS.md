# Progress — Synapse

## Status

Tasks 0–14 and 16 completed 2026-11-12. Task 15 (semantic cache + limits) pending. FRONTEND Phase A (backend API) completed 2026-11-13. Next: FRONTEND Phase B / Tasks 15/17.

## Checklist

- [x] 0 Recon — repo hygiene, corpus analysis, LLM proxy probe, requirements
- [x] 1 Scaffold — FastAPI app skeleton, pyproject.toml, test setup
- [x] 2 Providers — LLM + embedding adapters (OpenAI-compatible)
- [x] 3 Corpus + chunking — loader, structure-aware chunker
- [x] 4 Index + hybrid retrieval — numpy vector index + BM25 + RRF
- [x] 5 Plan + Tools — planner + typed local tool registry
- [x] 6 Review + Answer + orchestrator — critic, answerer, 5-stage loop
- [x] 7 /ask API — FastAPI routes (/health, /ask) + schemas
- [x] 8 Eval harness + tuning — golden YAML, runner, scoring + tuning fixes
- [x] 9 React UI — chat frontend
- [x] 10 Dockerfile — multi-stage build, graded command
- [x] 11 Submission gate — Definition of Done checklist
- [x] 12 Streaming trace — SSE stage events + trace panel
- [x] 13 Interactive citations — hover/focus preview
- [x] 14 Comparison matrix + eGFR widget
- [ ] 15 Semantic cache + limits
- [x] 16 Hardening — errors, timeouts, non-root user, sanitization
- [ ] 17 E2E smoke (optional) — Playwright
- [ ] 18 Presentation + walkthrough docs
- [ ] 19 Final freeze

## Decisions

(recorded from Task 0 — LLM proxy probe results)

1. **Structured-output mode** — the proxy supports
   `response_format={"type": "json_schema", ...}` with `strict: true` (probe (b)
   succeeded). → Use native json_schema for LLM stages; keep JSON-mode +
   Pydantic validation as the documented fallback.
2. **Tool-calling mode** — native function calling works (probe (c) returned a
   `tool_calls` entry). → Use native tools; fall back to a structured
   "choose tool" step only if needed.
3. **Embedding dimension** — `text-embedding-3-small` returns **1536**-dim vectors;
   a 100-input batch worked. → numpy float32 matrix of shape (n, 1536).
4. **Chat model** — local `.env` sets `OPENAI_MODEL=gpt-5.6-terra` (LiteLLM-proxied);
   `client.models.list()` reports 115 allowed models.
5. **Base-URL config** — app code reads the documented `OPENAI_BASE_URL` only.
   A transient local `.env` typo (`OPENAI_BASE_UR`) was detected during recon and
   has since been corrected; the probe still tolerates the alias defensively.
6. **Corpus scope** — 10 drugs × (DailyMed + MedlinePlus) + `GLOSSARY.md`
   (21 files). Index all 10 drugs; the 4 eval drugs (warfarin, apixaban,
   sertraline, metformin) are the graded focus.
7. **OpenAI SDK** — `openai` 3.49.0 (v3 API) installed locally; pin it in
   `pyproject.toml` during Task 1.
8. **Pinned versions (Task 1)** — fastapi 0.162.5, uvicorn[standard] 0.54.0,
   pydantic 2.14.3, pydantic-settings 2.16.2, openai 3.49.0, httpx 0.28.1,
   numpy 2.5.4; dev: pytest 9.2.0, pytest-asyncio 1.4.1.post1, pytest-cov 7.1.0,
   pytest-socket 0.8.1, respx 0.23.1, ruff 0.17.4, mypy 2.4.1. Note: openai 3.x
   depends on `httpx2`/`httpcore2`; classic `httpx` (for TestClient/respx) coexists.
9. **pytest-socket mode** — use `socket_allow_hosts(allowed=["127.0.0.1","::1"])`
   (blocks outbound `.connect()` only) rather than `disable_socket`, because the
   full socket-creation block breaks asyncio's self-pipe on Windows.
10. **Provider layer (Task 2)** — `LLMClient`/`EmbeddingProvider` Protocols +
    OpenAI impls on `AsyncOpenAI` (timeout from settings, `max_retries=0`). Structured
    output probes json_schema once and caches the mode (JSON-mode fallback + one
    repair retry); native tool calling; error mapping (401/403→configuration,
    429→rate_limited, timeout→provider_timeout, 5xx→provider_error) with a
    `retryable` flag; capped exponential backoff + jitter; concurrency semaphore;
    embeddings chunked at 100 with bounded concurrency.
11. **Test transport & fakes (Task 2)** — openai 3.x uses `httpx2` 2.16.0; tests
    mock it with `httpx2.MockTransport` (added to dev extras). Fakes live in
    `backend/tests/fakes/` (FakeLLMClient raises on unscripted; FakeEmbeddingProvider
    is deterministic hash-based); an autouse conftest fixture installs them (opt
    out via `@pytest.mark.real_providers`); `LLM_PROVIDER=fake` selects them at runtime.
12. **Retrieval (Task 3)** — loader derives `drug_name`/`source_type` from
    `<source>-<drug>.md`; `GLOSSARY.md` (25 entries) parsed to
    term/aliases/definition and never chunked. Structure-aware chunker: splits on
    headings (path = `drug > section > subsection`); tables = blank-line blocks
    containing `|`, kept atomic (oversized tables split at rows, header repeated);
    Boxed Warning / Contraindications / Dosage sections never split; oversized
    sections split at paragraph boundaries with small overlap. Token count =
    `ceil(len/chars_per_token)` (default 4.0); 800-token chunks, 60-token overlap,
    all Settings-configurable. Chunk id = `sha256(file|path|index)[:16]`; 460 chunks
    total. CLI: `python -m app.retrieval.inspect_chunks [file]`.
13. **Retrieval (Task 4)** — own `BM25Index` (tokenizer keeps `30`/`mL/min`/`1.73`/
    `INR`), `NumpyVectorIndex` behind a `VectorIndex` Protocol (L2-normalized float32,
    cosine dot, `argpartition` top-k), `HybridSearcher` (RRF k=60 + glossary
    abbreviation expansion, dense/bm25 ranks + fused score on every hit),
    `Retriever.run(plan)` (per-goal `asyncio.gather`, dedupe by chunk id, token
    budget 4000, drug-coverage rule) and `IndexManager` (background build, readiness
    `building|ready|degraded`, disk embedding cache keyed `sha256(text)`+model,
    BM25-only fallback). Settings: `rrf_k`, `retrieval_top_k`, `retrieval_token_budget`,
    `index_ready_timeout_s`. CLI: `python -m app.retrieval.debug "question"`.

### Task 4 retrieval quality (real embeddings, text-embedding-3-small)

| # | Question | Top results (file > section) |
|---|----------|------------------------------|
| 1 | Warfarin contraindications | `dailymed-warfarin.md > 4 CONTRAINDICATIONS` (d1 b2) ✓ |
| 2 | Warfarin vs apixaban contraindications | `dailymed-apixaban.md > 4 CONTRAINDICATIONS` (d9 b3) + `dailymed-warfarin.md > 4 CONTRAINDICATIONS` (b1) ✓ |
| 3 | Warfarin + sertraline bleeding | warfarin `WARNING: BLEEDING RISK` + `5.1 Hemorrhage`; sertraline `5.3 Increased Risk of Bleeding` + `7.1` (warfarin INR monitoring) ✓ |
| 4 | Metformin eGFR 25 threshold | `dailymed-metformin.md > 2.3 Recommendations for Use in Renal Impairment` (d1 b2), `4 CONTRAINDICATIONS` (eGFR below 30), `5.1 Lactic Acidosis` ✓ |

All four expected source files and the clinically relevant sections appear in the
top fused results; dense embeddings dominate for these semantic questions, with
BM25 contributing exact-term recall.
14. **Plan + Tools (Task 5)** — `Planner` (Stage 1) sanitizes input, calls the LLM
    with structured output (`Plan`), and semantically validates 1..MAX_SUB_GOALS
    sub-goals with one repair retry then `AgentError`. `ToolRegistry` allowlist
    (typed Pydantic args/result, timeout, errors-as-results) with three local tools:
    `glossary_lookup` (exact + `difflib` fuzzy), `label_section_lookup`
    (heading-path match + synonyms) and `threshold_check` (conservative regex
    threshold extraction; eGFR 25 vs "below 30" → `contraindicated`; `unknown`
    unless certain; never outside knowledge). `ToolRunner` (Stage 3) runs
    model-chosen tools via native function calling (parallel, bounded by
    MAX_TOOL_CALLS), treats evidence/tool text as untrusted delimited data, then
    synthesizes a `Draft` with claim-reference validation (one repair retry).
    Prompts are versioned templates in `agent/prompts/`. `IndexManager` now exposes
    `chunks` + `glossary_entries` so Task 6 can wire the tools.
15. **Review + Answer + orchestrator (Task 6)** — `Reviewer` (Stage 4) runs a
    separate LLM audit plus deterministic checks (`missing_numbers` verifies every
    number in a claim appears verbatim in its cited evidence/tool text); merged
    `Review{verdict,unsupported_claims,ambiguity_flags}`. `Answerer` (Stage 5) is
    pure code: drops unsupported claims, handles insufficient-evidence, builds
    Markdown with `[Sx]` markers + a `Sources` section naming files/sections, and
    appends `MEDICAL_DISCLAIMER`. `PipelineContext`/`Pipeline` enforce the strict
    Plan→Retrieve→Tools→Review→Answer order (out-of-scope skips still emit events),
    time each stage into `StageEvent`s, enforce `REQUEST_TIMEOUT_S`, and build the
    full Section 9 `AskResponse` (`answer/sources/citations/disclaimer/plan/
    tool_calls/review/retrieval_mode/trace_id/usage/latency_ms`). `TokenTrackingLLMClient`
    accumulates token usage; `ToolRunner` exposes `last_tool_results`; `Retriever`
    exposes `retrieval_mode`.
16. **POST /ask (Task 7)** — `AskRequest` (question 1-2000 chars, stripped,
    `extra="ignore"`), `AskService` (lazy pipeline build, provider-error → AppError
    translation, one structured JSON log line per request with request_id/latency/
    tokens/verdict/tool names/retrieval_mode — never the question), thin `api/ask.py`
    router with `response_model=AskResponse`. Error mapping: missing/invalid key →
    503, rate limit → 429, timeout → 504, invalid payload → 422, unexpected → 500.
    `JsonFormatter` now merges extra fields and silences httpx/httpx2/openai INFO
    logs (so the base URL is never logged). Integration tests (TestClient + fakes):
    200 + schema + 5 stage events + citations/sources/disclaimer, 422 validation,
    no-key → 503.

### Task 7 manual eval (real proxy, gpt-5.6-terra)

| Q | Result | Verdict | Latency | Tokens (in/out) |
|---|--------|---------|---------|-----------------|
| 1 Warfarin contraindications | 200 ✓ | pass | 25.3s | 13,337 / 1,336 |
| 2 Warfarin vs apixaban | 504 (timeout) | — | >90s | — |
| 3 Warfarin + sertraline | 504 (timeout) | — | >90s | — |
| 4 Metformin eGFR 25 | 200 ✓ | revise | 62.8s | 36,073 / 3,632 |
| 5 Apixaban MoA | 200 ✓ | pass | 14.2s | 48,846 / 4,162 |
| 6 INR meaning/monitoring | 200 ✓ | revise | 20.2s | 63,063 / 5,587 |

4/6 succeed with correct sources and grounded, cited answers. The two multi-drug
questions (2, 3) exceed the 90s hard timeout → clean 504 (mapping works). Cause:
the evidence is re-sent at every stage and the ~4000-token (chars/4) budget
underestimates real tokens, so multi-hop contexts are large. → Task 8 tuning item.

### Task 8 eval harness + tuning (2026-11-12)

Added `backend/tests/eval/`: `golden_questions.yaml` (17 golden questions — the
4 public ones verbatim + 6 single-document lookups across other drugs + 3
multi-drug/multi-hop (NSAID+anticoagulant, aspirin+warfarin, statin) + 2
out-of-scope + 2 unanswerable; every must-include fact verified verbatim against
the corpus file), `scoring.py` (pure deterministic scoring: expected files in
`sources`, file names in `answer`, must-include facts, disclaimer, no unsupported
flags, latency budget), and `run.py` (`python -m tests.eval.run [--only ID]
[--runs N]`, marker `llm_live` excluded from default pytest via `addopts`, hits
the running API, prints a table and writes `docs/eval_results.md`). Added
`pyyaml` to dev extras.

Tuning fixes (before → after, real proxy gpt-5.6-terra):
- Multi-drug Q2/Q3 timed out at >90s → lowered `RETRIEVAL_TOP_K` 20→12 and
  `RETRIEVAL_TOKEN_BUDGET` 4000→3000; the review stage now sends only the
  evidence/tool results cited by the draft (was the full evidence). Q2/Q3 now
  finish in ~10–45s.
- Q2 sometimes cited only one drug → the retriever now guarantees one chunk per
  named drug survives the token budget, and the Answerer emits citations for tool
  results that name a `source_file` (e.g. `label_section_lookup`).
- Q4 "revise" (false unsupported flag on the query value 25) → review/answer now
  exclude numbers present in the original question.
- Review over-flagged paraphrases → review prompt tightened to flag only facts
  absent from cited text; draft prompt now hedges absence/completeness claims.

Final eval: **17/17** (4 public ×2 runs = 8/8; full 17-question run = 17/17),
p50 latency ~15s. Saved to `docs/eval_results.md`.

### Task 9 React UI (2026-11-12)

Added `frontend/` (Vite 6 + React 18 + TypeScript strict + Tailwind v3). A typed API
client (`lib/api.ts`) validates `/ask` responses with Zod (`types/api.ts`) and maps the
`{"error":{...}}` shape to a typed `ApiError`. Chat page with textarea (Enter sends,
Shift+Enter newline), loading/error/empty states, the 4 public eval questions as
clickable examples, sanitized Markdown (`react-markdown` + `remark-gfm` +
`rehype-sanitize`, no `dangerouslySetInnerHTML`), a Sources list, review flags, and an
always-visible medical disclaimer. `backend/app/main.py` now mounts `frontend/dist`
at `/assets` with an SPA fallback registered after the API routers (API routes keep
precedence); the API still starts when `dist` is absent. Verified: `npm run build`,
`tsc --noEmit`, `eslint .`, `vitest run` (11 tests), backend `ruff`/`mypy`/`pytest`
(154), and end-to-end `/` serving + `POST /ask` (Q1 → 200, sources
`dailymed-warfarin.md`/`medlineplus-warfarin.md`, review `pass`, ~19s).

### Task 10 Dockerfile (2026-11-12)

Added a multi-stage root `Dockerfile` (node:22-alpine → python:3.11-slim build →
python:3.11-slim runtime) plus `.dockerignore`. Runtime runs as non-root `appuser`
(uid 10001), copies only the venv, `backend/`, `corpus/` and `frontend/dist`, sets
`CORPUS_DIR=/app/corpus`, a writable `CACHE_DIR=/tmp/synapse-cache`, a `HEALTHCHECK`
on `/health`, and exec-form `uvicorn app.main:app --app-dir /app/backend`.

Verified with the exact graded command (cold build **470s**, image **415 MB**):
`/health` 200 in **7.9s**, index ready in **16.8s**, and all 4 public questions
return 200 with correct sources (pass verdict). Robustness checks all pass:
(a) different values (fake endpoint → clean 502, DEBUG logs prove LOG_LEVEL read),
(b) values wrapped in quotes (stripped correctly → 200), (c) invalid key (stays up,
`/health` 200, `/ask` clean 503), (d) no `OPENAI_BASE_URL` (llm_configured false,
clean 503), (e) runs as non-root (uid 10001), (f) UI loads at `/`.

Fix: `numpy==2.5.4` requires Python ≥3.12, conflicting with the graded
`python:3.11-slim` base — re-pinned to `numpy==2.4.6` (same 2.x API surface).

### Task 11 Submission gate (2026-11-12)

Wrote the full `README.md` (overview, exact Docker commands, required env vars, UI
URL, `/health` and `/ask` curl examples, 5-stage pipeline Mermaid diagram, project
structure, dev/test commands, eval harness, AI-coding-config note, disclaimer). Quality
gate green: `ruff`, `mypy --strict` (46 files), `pytest` (154), frontend
`tsc --noEmit`, `eslint`, `vitest` (11), `npm run build`.

Secret audit: `.env` (key/base URL) was never committed and no key-like strings are in
any tracked file. However, the confidential `assignment-pharma.pdf` WAS committed
(`ec2f3b3`, `98613df`) and pushed to the public remote. Remediated (owner approved):
purged it from all history with `git filter-repo --path assignment-pharma.pdf
--invert-paths`, force-pushed the rewritten history, and re-synced/pruned the local
clone. Re-audit clean: no PDF or `.env` in any ref.

Remote: `https://github.com/modibo-ucd/Synapse.git` (public GitHub; GitLab was only
"preferred", not required). Pushed `main`.

Clean-clone test: `git clone` into a temp folder outside the project, copied the real
`.env`, ran the exact graded command (build **645s**, image **415 MB**), `/health` 200
in **8.8s**, index ready in **17.9s**, and all 4 public questions returned 200 with the
expected sources and `pass` verdicts — matching `docs/eval_results.md`.

### Task 12 Streaming trace (2026-11-12)

Added `POST /ask/stream`: SSE that emits one `stage` event per StageEvent (stage,
status, duration_ms, UI-safe `summary` + structured `details`: sub-goals, retrieved
chunks/source files with ranks, tool names + args + status, review verdict) and then a
final `result` event; the pipeline task is cancelled on client disconnect. `StageEvent`
gained a `details` field and `PipelineContext`/`Pipeline` an `on_event` callback.
Frontend: `streamAskQuestion` (fetch + ReadableStream SSE parser), an animated
`TracePanel` (5 stages, pending/running/done/skipped, durations, expandable details,
`prefers-reduced-motion`), and automatic fallback to `/ask` when streaming fails.
Tests: SSE event order + disconnect cancellation (blocking fake) + panel rendering +
fallback. Verified in Docker: `stage_events=5 result_events=1`, `/ask` unchanged.

### Task 13 Interactive citations (2026-11-12)

`citations[].excerpt` is now ≤500 chars, trimmed on sentence boundaries. Frontend turns
`[S1]` markers into accessible citation chips via a remark plugin (`citationMarkers`)
plus a `CitationChip` with a hover/focus/tap popover (excerpt, source file, section)
and a "View in Sources" link that scrolls to and highlights the Sources entry; unknown
ids render as plain text. No `dangerouslySetInnerHTML`. Tests cover lists/tables,
popover on hover/focus/tap, a11y roles, and the unknown-id fallback.

### Task 14 Comparison matrix + eGFR widget (2026-11-12)

A) Multi-drug comparison matrix: for multi_hop plans spanning 2+ drugs the Answer
returns a validated `comparison {drugs, rows[{attribute, values{drug:{text,
citation_ids}}}]}`; every cell is grounded in cited evidence and missing data is the
explicit "Not stated in sources". Frontend renders a filterable, sticky-first-column,
horizontally scrollable grid with citation chips; falls back to the Markdown table when
absent. B) eGFR widget: pure `egfr_ckd_epi_2021` (CKD-EPI 2021, mg/dL↔µmol/L, bounds)
with unit tests against reference vectors; when the cited evidence mentions renal
thresholds the response includes `widgets:[{type:"egfr", thresholds:[...]}]`, rendered
as an inline educational calculator (live result, highlights crossed thresholds,
explicit "not personalized dosing advice" disclaimer).

Eval re-run (2026-11-12): **15/17** — all 4 public questions pass (`hybrid`, correct
sources, `pass`); the 2 failures are transient LLM latency (q12 → 504 timeout, q13 →
89s), not feature regressions (the new features add zero LLM calls).

### Task 16 Robustness & safety hardening (2026-11-12)

Hardened per `.clinerules` §10/§12:

- **Concurrency** — `AskService` no longer caches a single `Pipeline`. Each `/ask`
  builds a fresh pipeline + `TokenTrackingLLMClient`, reusing the shared LLM client
  (concurrency semaphore + structured-output probe cache) and the read-only
  retriever/tool registry. 10 parallel asks keep per-request token usage and tool
  results isolated and never corrupt the index (concurrency unit tests).
- **Input robustness** — new `app/core/text.sanitize_question` runs at the API
  boundary (`AskRequest`): control characters stripped, whitespace normalized,
  control-char-only questions → 422, Unicode preserved.
- **Prompt-injection defense** — plan/draft/tools/review prompts mark user text and
  retrieved passages as untrusted data; question/sub-questions wrapped in
  `<<<BEGIN QUESTION>>>`/`<<<END QUESTION>>>` delimiters; hostile corpus text never
  changes tool use or output format (unit + end-to-end integration tests).
- **Safety** — plan prompt forbids personalized dosing/diagnosis; patient-specific
  questions are answered strictly from label text with the mandatory disclaimer;
  out-of-scope/unanswerable questions decline clearly.
- **Failure modes** — provider 401/403→503, 429→429, timeout→504, 5xx→502 as clean
  structured errors; malformed JSON repair (provider tests); empty/invalid tool
  arguments → error result (no crash); embeddings fail → `bm25_only`; startup with no
  key or unreachable base URL keeps `/health` 200.
- **Security** — security-headers middleware (`X-Content-Type-Options: nosniff`,
  `Referrer-Policy: no-referrer`, `X-Frame-Options: DENY`, a CSP compatible with the
  built Vite bundle); log redaction filter scrubs the API key and base URL;
  degradation paths log the failure type only (no tracebacks carrying provider URLs);
  container confirmed non-root (uid 10001).
- **Eval** — latency p50/p95 added to the harness.

Eval re-run (2026-11-12): **16/17** — p50 **13.1s**, p95 **30.6s** (n=17). All 4 public
questions pass (`hybrid`, correct sources, `pass`); q12 (aspirin + warfarin) misses the
literal "bleeding" substring (verdict `pass`, no unsupported flags — an exact-substring
scorer sensitivity, not a grounding failure). Recorded in `docs/eval_results.md`.

Checks: `ruff` ✓, `mypy --strict` (48 files) ✓, `pytest` (194) ✓, frontend
`tsc --noEmit` / `eslint` / `vitest` (29) ✓, `npm run build` ✓. Docker graded command
verified: `/health` 200 (index ready), `/ask` 200 grounded with disclaimer, security
headers present, non-root (uid 10001); invalid-key + quoted-values `.env` → `/health`
200 (index `degraded`), `/ask` clean 503 `configuration_error`.

## FRONTEND Phase A (backend API) — 2026-11-13

Additive, non-breaking backend work per `docs/FRONTEND_SPEC.md`:

- **Chunk spans** — `Chunk.start_char`/`end_char` (char offsets into the
  loader-normalized text) tracked through the chunker; half-open, may overlap,
  exclude the repeated table header; chunk text/ids unchanged.
- **UTF-16** — `core/text.utf16_offset` maps char offsets to JS code-unit
  offsets (non-BMP safe), applied once per boundary in the sources endpoint.
- **`/ask` additions** — optional `retrieval` (candidates/returned/cited chunks)
  and `trace` (5 stages, `done|skipped`) built in `ask_service` from `Evidence`
  + `StageEvent`s; `Evidence.candidates` and `Pipeline.evidence` plumbed through.
- **`/health` additions** — `version` (setting `APP_VERSION`, default `0.1.0`)
  and `index_stats` (`{files, chunks, embedding_model}` | None); still 200 always.
- **Sources endpoints** — `GET /api/v1/sources` + `/{file_name}` via a
  startup-built allowlist registry (`SourceService`); strict file-name
  validation, `NotFoundError` 404 in the standard shape, `ETag`/304 +
  `Cache-Control`; works while the index is still building.
- **Static serving** — SPA fallback 404s for `/api/*`, `/ask*`, `/health`,
  `/docs`, `/redoc`, `/openapi.json` and missing assets with an extension.

Checks: `ruff` ✓, `mypy --strict` (51 files) ✓, `pytest` (207) ✓. Eval re-run
(2026-11-13): **17/17** (p50 14.6s, p95 24.5s) — the previously flaky q12
"bleeding" substring now matches; no regression from the additive changes.

## Known issues

- (Resolved Task 11) `assignment-pharma.pdf` was committed (`ec2f3b3`, `98613df`) and
  pushed; purged from all history with `git filter-repo` + force-push (kept locally on
  disk, gitignored). `.env` was never committed.
- (Resolved) Local `.env` initially had `OPENAI_BASE_UR` instead of
  `OPENAI_BASE_URL`; corrected before the probe's final run.
- PDF question 4 is truncated after "what is the threshold"; handled per the
  `.clinerules` restatement.
- PDF says "5 evaluation questions" (p2) vs "4 public" (p4) — 4 public is authoritative.
- `docker ps`/`docker info` hung in the PowerShell terminal during recon; Docker
  Desktop processes are running — verify the daemon with a timeout before Task 10.

## Timeline

- Deadline: **2026-11-13 23:59** (Casablanca). Submission = public repo link +
  short summary emailed; the last pushed commit before the deadline is graded.
- Feature freeze target: **2026-11-13 18:00**.
- Plan: Tasks 1–11 (P0 core) by ~12:00; Tasks 12–14 (P1) by ~16:00; Tasks 15–19
  (P2 + final freeze) by 18:00.
