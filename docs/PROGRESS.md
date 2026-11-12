# Progress — Synapse

## Status

Tasks 0–7 completed 2026-11-12. Next: Task 8 (Eval harness + tuning).

## Checklist

- [x] 0 Recon — repo hygiene, corpus analysis, LLM proxy probe, requirements
- [x] 1 Scaffold — FastAPI app skeleton, pyproject.toml, test setup
- [x] 2 Providers — LLM + embedding adapters (OpenAI-compatible)
- [x] 3 Corpus + chunking — loader, structure-aware chunker
- [x] 4 Index + hybrid retrieval — numpy vector index + BM25 + RRF
- [x] 5 Plan + Tools — planner + typed local tool registry
- [x] 6 Review + Answer + orchestrator — critic, answerer, 5-stage loop
- [x] 7 /ask API — FastAPI routes (/health, /ask) + schemas
- [ ] 8 Eval harness + tuning — evaluation of the public questions
- [ ] 9 React UI — chat frontend
- [ ] 10 Dockerfile — multi-stage build, graded command
- [ ] 11 Submission gate — Definition of Done checklist
- [ ] 12 Streaming trace — SSE stage events + trace panel
- [ ] 13 Interactive citations — hover/focus preview
- [ ] 14 Comparison matrix + eGFR widget
- [ ] 15 Semantic cache + limits
- [ ] 16 Hardening — errors, timeouts, non-root user, sanitization
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

## Known issues

- `assignment-pharma.pdf` was tracked in git; removed from the index with
  `git rm --cached` (file kept locally on disk).
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
