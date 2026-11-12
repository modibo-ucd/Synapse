# Synapse — Agentic Pharmacology Research Assistant

Synapse answers compound pharmacology questions from a local corpus of FDA/DailyMed
drug labels and MedlinePlus patient monographs. It runs a strict five-stage agent
pipeline — **Plan → Retrieve → Tools → Review → Answer** — and returns a **cited**
Markdown answer that names its source files and always ends with a medical disclaimer.

This is a research/educational tool, **not medical advice**. It does not diagnose,
prescribe, or give personalized dosing instructions; it answers strictly from the
retrieved label text and says "insufficient evidence" when the corpus does not support
an answer.

---

## Quick start (Docker — the graded path)

The container is fully self-contained: the only external dependency is your
OpenAI-compatible endpoint. Build and run it with the exact graded command:

```bash
docker build -t agent .
docker run -p 8000:8000 --env-file .env agent
```

Then open the UI at **http://localhost:8000/** or call the API directly (see below).

### Required environment variables

Create a `.env` file (see `.env.example` for placeholders). Only these four are
required; every other setting has a safe default:

| Variable                 | Required | Default                  | Purpose                        |
| ------------------------ | -------- | ------------------------ | ------------------------------ |
| `OPENAI_API_KEY`         | yes      | —                        | API key for the LLM proxy      |
| `OPENAI_BASE_URL`        | yes      | —                        | OpenAI-compatible base URL     |
| `OPENAI_MODEL`           | yes      | —                        | Chat model name                |
| `OPENAI_EMBEDDING_MODEL` | no       | `text-embedding-3-small` | Embedding model name           |

`GET /health` always returns HTTP 200 — even while the in-memory index is still
building, or when the LLM endpoint is unreachable or the key is missing. If embeddings
are unavailable the app degrades to BM25-only retrieval (reported as
`retrieval_mode: "bm25_only"`).

---

## API

### Health

```bash
curl http://localhost:8000/health
# {"status":"ok","index":"ready","llm_configured":true}
```

### Ask

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the main contraindications for warfarin?"}'
```

The response contains Markdown with inline `[S1]` markers, a `sources` list naming the
source files, per-citation excerpts, a `review` verdict, and the mandatory disclaimer:

```json
{
  "answer": "… cited Markdown …",
  "sources": ["dailymed-warfarin.md"],
  "citations": [
    { "id": "S1", "source_file": "dailymed-warfarin.md", "section": "Contraindications", "excerpt": "…" }
  ],
  "disclaimer": "…",
  "plan": { "complexity": "simple", "sub_goals": [] },
  "tool_calls": [],
  "review": { "verdict": "pass", "unsupported_claims": [], "ambiguity_flags": [] },
  "retrieval_mode": "hybrid",
  "trace_id": "…",
  "usage": { "tokens_in": 0, "tokens_out": 0 },
  "latency_ms": 0
}
```

---

## The five-stage pipeline

```mermaid
flowchart LR
    Q([Question]) --> P["1. Plan<br/>decompose into sub-goals"]
    P --> R["2. Retrieve<br/>dense + BM25 + RRF"]
    R --> T["3. Tools + Draft<br/>agent-chosen local tools"]
    T --> V["4. Review<br/>grounding check"]
    V --> A["5. Answer<br/>cited response"]
    A --> O([Cited answer + disclaimer])
```

1. **Plan** — decompose the question into sub-goals (one per drug, plus a comparison
   sub-goal for multi-drug questions).
2. **Retrieve** — fetch passages with in-memory hybrid retrieval (numpy cosine + BM25 +
   Reciprocal Rank Fusion), guaranteeing coverage of every named drug.
3. **Tools + Draft** — the agent selects from typed, deterministic local tools
   (`glossary_lookup`, `label_section_lookup`, `threshold_check`) via native function
   calling and drafts a grounded answer in which every claim cites evidence or a tool
   result.
4. **Review** — a separate critic verifies each claim against its cited source and flags
   unsupported or clinically ambiguous wording before the answer is emitted.
5. **Answer** — assemble a cited response that names its source files and appends the
   medical disclaimer (added by code, never by the model).

---

## Project structure

```text
.
├── Dockerfile              # multi-stage build (Node → Python build → runtime)
├── pyproject.toml          # pinned Python dependencies + tool configuration
├── corpus/                 # FDA/DailyMed + MedlinePlus Markdown + GLOSSARY.md
├── backend/
│   ├── app/
│   │   ├── main.py         # app factory; also serves the built UI
│   │   ├── api/            # thin routers: /health, /ask
│   │   ├── core/           # config, logging, errors, constants
│   │   ├── schemas/        # Pydantic v2 request/response/domain models
│   │   ├── services/       # ask_service (pipeline orchestration)
│   │   ├── providers/      # OpenAI-compatible LLM + embedding adapters
│   │   ├── retrieval/      # loader, structure-aware chunker, BM25, vector index, hybrid
│   │   └── agent/          # 5-stage pipeline, tools, review, answer, prompts
│   └── tests/              # unit/, integration/, eval/ (golden harness), fakes/
├── frontend/
│   └── src/                # components/, features/chat/, lib/, types/
├── scripts/                # dev helpers (LLM probe, eval smoke)
└── docs/                   # requirements, progress, evaluation results
```

---

## Development & tests

Backend (Python 3.11+, run from the repo root):

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
ruff check backend               # lint
mypy                             # type check (--strict)
pytest                           # unit + integration (zero real LLM calls)
```

Frontend (Node 18+, run from `frontend/`):

```bash
npm ci
npm run build                    # tsc --noEmit && vite build
npm run typecheck                # tsc --noEmit
npm run lint                     # eslint
npm run test                     # vitest
```

Unit tests never call a real LLM — an autouse fixture installs deterministic fakes that
raise on any unscripted call, and `pytest-socket` blocks outbound network.

### Evaluation harness (live LLM)

`backend/tests/eval/` holds 17 golden questions (the 4 public ones verbatim, plus
single-document and multi-drug lookups, out-of-scope and unanswerable cases). With the
API running and a real `.env`:

```bash
python -m tests.eval.run --base-url http://localhost:8000 --runs 2
python -m tests.eval.run --only q1     # single question
```

It scores deterministically (expected files cited, file names present in `answer`,
must-include facts, disclaimer, no unsupported flags, latency) and writes
`docs/eval_results.md`. It is excluded from the default `pytest` run (marker `llm_live`).

---

## AI-assisted development

This repository was developed with AI coding assistance. The assistant's working
agreement is committed in `.clinerules`, and `docs/` records the requirements, progress,
and evaluation results.

---

## Disclaimer

This project provides research and educational information only and is **not medical
advice**. It is generated from drug labeling and consumer medication documents and must
not be used to diagnose, treat, or make prescribing decisions. Always consult a
qualified healthcare professional.

