"""Pydantic v2 domain models shared by retrieval and the agent pipeline."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

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
