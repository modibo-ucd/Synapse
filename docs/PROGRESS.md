# Progress — Synapse

## Status

Task 0 (Recon, LLM proxy probe, repo hygiene) completed 2026-11-12. Application
code starts with Task 1 (Scaffold).

## Checklist

- [x] 0 Recon — repo hygiene, corpus analysis, LLM proxy probe, requirements
- [ ] 1 Scaffold — FastAPI app skeleton, pyproject.toml, test setup
- [ ] 2 Providers — LLM + embedding adapters (OpenAI-compatible)
- [ ] 3 Corpus + chunking — loader, structure-aware chunker
- [ ] 4 Index + hybrid retrieval — numpy vector index + BM25 + RRF
- [ ] 5 Plan + Tools — planner + typed local tool registry
- [ ] 6 Review + Answer + orchestrator — critic, answerer, 5-stage loop
- [ ] 7 /ask API — FastAPI routes (/health, /ask) + schemas
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
