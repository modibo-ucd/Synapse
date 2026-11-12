# Requirements — Synapse: Agentic Pharmacology Research Assistant

Source of truth: `assignment-pharma.pdf` (confidential; kept locally, never committed).
`.clinerules` mirrors these rules. If they conflict, the PDF wins.

## 1. Objective

Build a small agentic research assistant in **Python** that answers compound
questions about a provided local corpus of pharmacology text files. Window
2026-11-11 → 2026-11-13 (3 calendar days); ~1 focused day of effort. This is a
technical exercise, not medical advice.

## 2. Mandatory interface (graded)

- Root `Dockerfile`; graders run exactly:
  `docker build -t agent . && docker run -p 8000:8000 --env-file .env agent`
- The container is self-contained: no external service besides the OpenAI-compatible
  LiteLLM endpoint. No Postgres/pgvector/Redis/Docker Compose.
- Graders inject their own `.env`. Only these are guaranteed: `OPENAI_API_KEY`,
  `OPENAI_BASE_URL`, `OPENAI_MODEL`, `OPENAI_EMBEDDING_MODEL`. Every other setting
  needs a safe default.
- `GET /health` → 200 always (even while the index is building or the LLM is down).
- `POST /ask` with `{"question": "..."}` → 200 with an answer. No auth, no extra headers.
- A minimal frontend served by the same container at `/` that calls `POST /ask`.

## 3. Mandatory agent behavior (5 stages, in order)

1. **Plan** — decompose the question into sub-questions/steps.
2. **Retrieve** — fetch relevant passages via in-memory similarity.
3. **Tools** — at least two local tools, chosen by the agent via native function
   calling (never hardcoded / keyword-routed).
4. **Review** — a critic step verifies grounding and flags unsupported or
   clinically ambiguous claims before the answer is emitted.
5. **Answer** — a cited response naming the source file(s), with an explicit
   disclaimer that the output is not medical advice.

## 4. Public evaluation questions (4)

| # | Question | Expected source file(s) |
|---|----------|-------------------------|
| 1 | What are the main contraindications for warfarin? | `dailymed-warfarin.md` |
| 2 | Compare the contraindications of warfarin and apixaban. What conditions are shared and which are unique to each drug? | `dailymed-warfarin.md`, `dailymed-apixaban.md` |
| 3 | A patient currently on warfarin is prescribed sertraline. What is the risk of bleeding and what monitoring is recommended? | `dailymed-warfarin.md`, `dailymed-sertraline.md` |
| 4 | A patient with an eGFR of 25 mL/min is being considered for metformin. Is metformin contraindicated at this level of renal function, and what is the threshold | `dailymed-metformin.md` |

Hidden questions are held back by the reviewers and will be similar (single-document
lookups and multi-drug / multi-hop reasoning).

### Known PDF inconsistencies

- Page 2 says "a set of **5** evaluation questions"; page 4 says "**4** public
  evaluation questions". The table lists 4; we treat 4 public as authoritative.
- Question 4 is **cut off** in the PDF right after "what is the threshold".
  `.clinerules` restates it as "...and what is the threshold?" (metformin eGFR).

## 5. Deliverables

- Public Git repository link (GitLab preferred).
- A 10-minute presentation / code walkthrough highlighting: the problem addressed,
  the GenAI frameworks and tools used and why, the architecture and workflow, and
  key challenges (integration, advanced functionality) and how they were overcome.
- Evaluation criteria: Technical Competence, Innovation and Creativity,
  Problem-Solving.

## 6. Corpus inventory & structure (Task 0 recon)

### 6.1 Files (21 total, ~454 KB)

`GLOSSARY.md` plus 10 drugs, each with a DailyMed label and a MedlinePlus monograph:

| Drug | dailymed-*.md (bytes) | medlineplus-*.md (bytes) |
|------|----------------------:|--------------------------:|
| acetaminophen | 2,195 | 11,111 |
| albuterol | 29,341 | 7,029 |
| amoxicillin | 26,336 | 8,666 |
| apixaban | 47,838 | 10,323 |
| aspirin | 2,561 | 12,712 |
| atorvastatin | 46,661 | 8,589 |
| ibuprofen | 41,979 | 15,626 |
| metformin | 33,442 | 10,765 |
| sertraline | 77,083 | 10,839 |
| warfarin | 47,027 | 11,629 |

`GLOSSARY.md` = 2,868 bytes. Total ≈ 464,620 bytes (~454 KB).
`dailymed-acetaminophen.md` and `dailymed-aspirin.md` are tiny (~2 KB) and look
truncated; they are likely non-graded distractors.

### 6.2 Structure

- **No YAML front matter.** Each file starts with `# <Drug> (<source>)` then a
  plain `Source: <URL>` line.
- **DailyMed labels** use FDA section numbering as Markdown headings:
  `## WARNING: <boxed-warning text>` (top), then `## 1 INDICATIONS AND USAGE`,
  `## 2 DOSAGE AND ADMINISTRATION` (`### 2.x`, occasionally `####`),
  `## 3 DOSAGE FORMS AND STRENGTHS`, `## 4 CONTRAINDICATIONS`,
  `## 5 WARNINGS AND PRECAUTIONS` (`### 5.x`), `## 6 ADVERSE REACTIONS`,
  `## 7 DRUG INTERACTIONS` (`### 7.x`), `## 8 USE IN SPECIFIC POPULATIONS`, …,
  `## 12 CLINICAL PHARMACOLOGY`, `## 17 PATIENT COUNSELING INFORMATION`.
  Boxed-warning titles vary per drug (warfarin "BLEEDING RISK", metformin
  "LACTIC ACIDOSIS", sertraline "SUICIDAL THOUGHTS AND BEHAVIORS", apixaban
  "PREMATURE DISCONTINUATION … / SPINAL/EPIDURAL HEMATOMA").
- **Tables** are pipe-formatted Markdown (e.g. sertraline Table 1 dosage and
  Table 5 drug interactions; apixaban bleeding Tables 6/7). Must never be split
  mid-way by the chunker.
- **MedlinePlus monographs** use lay-language headings: `## IMPORTANT WARNING:`,
  `## Why is this medication prescribed?`, `## How should this medicine be used?`,
  `## Other uses for this medicine`, `## What special precautions should I follow?`,
  `## What special dietary instructions should I follow?`, etc.
- **GLOSSARY.md** format: `# Pharmacology Glossary` → `## Core concepts`,
  `## Pharmacokinetics`, `## Pharmacodynamics`, `## Safety and monitoring`,
  `## Reading drug labels`; each entry is `- **Term**: definition.`

### 6.3 Key clinical locations (for the 4 eval questions)

- **Warfarin contraindications** — `dailymed-warfarin.md` → `## 4 CONTRAINDICATIONS`
  (pregnancy; hemorrhagic tendencies/blood dyscrasias; recent CNS/eye surgery;
  active GI/GU/respiratory bleeding; CNS hemorrhage; cerebral aneurysm; etc.).
- **Warfarin bleeding risk** — `dailymed-warfarin.md` → `## WARNING: BLEEDING RISK`
  (boxed warning: major/fatal bleeding; regular INR monitoring; drug/diet effects
  on INR).
- **Apixaban contraindications** — `dailymed-apixaban.md` → `## 4 CONTRAINDICATIONS`.
- **Warfarin + sertraline bleeding** — `dailymed-sertraline.md` →
  `## 7 DRUG INTERACTIONS` → `### 7.1` Table 5, "Drugs that Interfere with
  Hemostasis (antiplatelet agents and anticoagulants)": concurrent use "may
  potentiate the risk of bleeding"; "For patients taking warfarin, carefully
  monitor the international normalized ratio". Warfarin is listed as an example
  (and again under "Drugs Highly Bound to Plasma Protein").
- **Metformin eGFR thresholds** — `dailymed-metformin.md`:
  - `### 2.3 Recommendations for Use in Renal Impairment` (contraindicated below
    30; initiation not recommended 30–45; reassess if it falls below 45;
    discontinue if below 30).
  - `## 4 CONTRAINDICATIONS` ("Severe renal impairment (eGFR below 30 mL/min/1.73 m²)").
  - `### 5.1 Lactic Acidosis` (contraindicated < 30; not recommended 30–45;
    annual eGFR monitoring).
  - `### 2.4 Discontinuation for Iodinated Contrast` (stop at eGFR 30–60).

### 6.4 Chunk/token estimate

- Total text ≈ 464 KB → roughly **100k–130k tokens** (≈4 bytes/token for English;
  tables are slightly denser).
- Structure-aware chunking (split on headings, preserve tables, never split
  Boxed Warning / Contraindications / Dosage sections) at a ~500–1000 token target
  → on the order of **a few hundred chunks** (exact count computed in Task 3).

## 7. Open questions

1. ~~Local `.env` typo `OPENAI_BASE_UR`~~ — resolved: `.env` now has
   `OPENAI_BASE_URL`. App code reads the documented name regardless.
2. Treat all 10 drugs as in-scope (current plan) or restrict indexing to the
   4 eval drugs? Current plan: index all 10.
3. Confirm the `dailymed-acetaminophen.md` / `dailymed-aspirin.md` truncation is
   intentional (likely non-graded distractors).
