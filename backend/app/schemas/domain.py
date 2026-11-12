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
