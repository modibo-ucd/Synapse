"""Pydantic v2 models for the source-document endpoints."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SourceDocType = Literal["dailymed", "medlineplus", "glossary"]


class SourceChunkSpan(BaseModel):
    """One chunk's location inside a source document (UTF-16 code units)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    chunk_id: str
    section_path: str
    start: int
    end: int


class SourceSummary(BaseModel):
    """One entry in the source list endpoint."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    file_name: str
    title: str
    drug_name: str
    source_type: SourceDocType
    size_chars: int


class SourceDocument(BaseModel):
    """A full source document plus its per-chunk UTF-16 character spans."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    file_name: str
    title: str
    drug_name: str
    source_type: SourceDocType
    markdown: str
    chunks: list[SourceChunkSpan] = Field(default_factory=list)
