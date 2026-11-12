"""Pydantic v2 domain models shared by retrieval and the agent pipeline."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

SourceType = Literal["dailymed", "medlineplus"]


class GlossaryEntry(BaseModel):
    """A single glossary term with optional aliases/abbreviations and category."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    term: str
    aliases: list[str] = Field(default_factory=list)
    definition: str
    category: str = ""


class CorpusDocument(BaseModel):
    """A raw corpus file (title + text) with metadata derived from its file name."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_file: str
    drug_name: str
    source_type: SourceType
    title: str
    raw_text: str


class Chunk(BaseModel):
    """A structure-aware chunk of a document, ready for embedding and retrieval."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    chunk_id: str
    source_file: str
    drug_name: str
    source_type: SourceType
    section_path: str
    section: str
    text: str
    embedding_text: str
    index: int
    token_count: int


PlanComplexity = Literal["simple", "multi_hop"]
RetrievalMode = Literal["hybrid", "bm25_only"]


class SubGoal(BaseModel):
    """A single sub-question produced by the planning stage (Stage 1)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    question: str
    intent: str = ""
    entities: list[str] = Field(default_factory=list)


class Plan(BaseModel):
    """Stage 1 output: the question decomposed into one or more sub-goals."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    complexity: PlanComplexity
    in_scope: bool
    sub_goals: list[SubGoal] = Field(default_factory=list)


class EvidenceChunk(BaseModel):
    """A retrieved chunk with dense/BM25 ranks and its fused score."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    chunk_id: str
    source_file: str
    drug_name: str
    source_type: SourceType
    section_path: str
    section: str
    text: str
    token_count: int
    dense_rank: int | None = None
    bm25_rank: int | None = None
    fused_score: float = 0.0


class Evidence(BaseModel):
    """Stage 2 output: deduplicated, budget-limited retrieved passages."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    chunks: list[EvidenceChunk] = Field(default_factory=list)
    retrieval_mode: RetrievalMode = "hybrid"


class Claim(BaseModel):
    """A single grounded claim, referencing evidence and/or tool results."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    text: str
    evidence_ids: list[str] = Field(default_factory=list)
    tool_result_ids: list[str] = Field(default_factory=list)


class Draft(BaseModel):
    """Stage 3 output: a tool-augmented draft with grounded claims + markdown."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    claims: list[Claim] = Field(default_factory=list)
    markdown: str = ""


ReviewVerdict = Literal["pass", "revise", "insufficient_evidence"]


class Review(BaseModel):
    """Stage 4 output: verdict plus unsupported claims and ambiguity flags."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    verdict: ReviewVerdict = "pass"
    unsupported_claims: list[str] = Field(default_factory=list)
    ambiguity_flags: list[str] = Field(default_factory=list)


class Citation(BaseModel):
    """A source citation for a [Sx] marker in the answer."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    source_file: str
    section: str
    chunk_id: str
    excerpt: str


class ToolCallRecord(BaseModel):
    """A single tool execution reported in the response."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    tool: str
    arguments: dict[str, Any]
    status: Literal["ok", "error"]


class ComparisonCell(BaseModel):
    """One grounded cell in the multi-drug comparison matrix."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    text: str
    citation_ids: list[str] = Field(default_factory=list)


class ComparisonRow(BaseModel):
    """One attribute row in the comparison matrix, keyed by drug name."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    attribute: str
    values: dict[str, ComparisonCell] = Field(default_factory=dict)


class Comparison(BaseModel):
    """A validated multi-drug comparison matrix (optional)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    drugs: list[str] = Field(default_factory=list)
    rows: list[ComparisonRow] = Field(default_factory=list)


class Usage(BaseModel):
    """Aggregated token usage across the pipeline."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    tokens_in: int = 0
    tokens_out: int = 0


class AnswerAssembly(BaseModel):
    """Stage 5 output: the assembled answer text and its citations."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    answer: str
    sources: list[str] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    disclaimer: str = ""
    comparison: Comparison | None = None


class AskResponse(BaseModel):
    """The full POST /ask response (Section 9 contract)."""

    model_config = ConfigDict(extra="forbid")

    answer: str
    sources: list[str] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    disclaimer: str = ""
    plan: Plan
    tool_calls: list[ToolCallRecord] = Field(default_factory=list)
    review: Review
    retrieval_mode: RetrievalMode
    trace_id: str
    usage: Usage
    latency_ms: float
    comparison: Comparison | None = None


class AskRequest(BaseModel):
    """POST /ask request body (tolerates harmless extra fields)."""

    model_config = ConfigDict(extra="ignore")

    question: str = Field(min_length=1, max_length=2000)

    @field_validator("question")
    @classmethod
    def strip_question(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("question must not be empty")
        return value
