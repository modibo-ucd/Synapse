"""Read-only registry of source documents for the /api/v1/sources endpoints.

The registry is built synchronously at startup, independently of the retrieval
index, so source documents are served even while the index is still building.
Chunk spans are converted from the chunker's character offsets into UTF-16 code
units so the frontend can slice the Markdown with JavaScript string indices.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from app.core.config import Settings
from app.core.errors import ConfigurationError, NotFoundError
from app.core.text import utf16_offset
from app.retrieval.chunker import chunk_documents
from app.retrieval.loader import load_documents, load_source_texts
from app.schemas.domain import Chunk
from app.schemas.sources import SourceChunkSpan, SourceDocument, SourceSummary

_GLOSSARY_FILE = "GLOSSARY.md"
_FILE_RE = re.compile(r"^[A-Za-z0-9._-]+\.md$")


def _title(markdown: str, fallback: str) -> str:
    """Return the first level-1 heading, falling back to a synthetic title."""
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return fallback


def _etag(text: str) -> str:
    return f'W/"{hashlib.sha256(text.encode("utf-8")).hexdigest()}"'


class SourceService:
    """Allowlist-backed access to the corpus Markdown and per-chunk spans."""

    def __init__(self, settings: Settings) -> None:
        corpus_dir = Path(settings.corpus_dir)
        texts = load_source_texts(corpus_dir)
        try:
            documents = load_documents(corpus_dir)
        except ConfigurationError:
            # A broken corpus must not crash startup: serve an empty registry.
            documents = []
        by_file = {doc.source_file: doc for doc in documents}

        chunks = chunk_documents(
            documents,
            max_tokens=settings.chunk_max_tokens,
            overlap_tokens=settings.chunk_overlap_tokens,
            chars_per_token=settings.chars_per_token,
        )
        chunks_by_file: dict[str, list[Chunk]] = {}
        for chunk in chunks:
            chunks_by_file.setdefault(chunk.source_file, []).append(chunk)

        allowlist = set(texts) & ({doc.source_file for doc in documents} | {_GLOSSARY_FILE})
        self._documents: dict[str, SourceDocument] = {}
        self._summaries: list[SourceSummary] = []
        for file_name in sorted(allowlist):
            markdown = texts[file_name]
            if file_name == _GLOSSARY_FILE:
                document = SourceDocument(
                    file_name=file_name,
                    title=_title(markdown, "Pharmacology Glossary"),
                    drug_name="glossary",
                    source_type="glossary",
                    markdown=markdown,
                    chunks=[],
                )
            else:
                corpus_doc = by_file[file_name]
                document = SourceDocument(
                    file_name=file_name,
                    title=corpus_doc.title,
                    drug_name=corpus_doc.drug_name,
                    source_type=corpus_doc.source_type,
                    markdown=markdown,
                    chunks=self._spans(markdown, chunks_by_file.get(file_name, [])),
                )
            self._documents[file_name] = document
            self._summaries.append(
                SourceSummary(
                    file_name=file_name,
                    title=document.title,
                    drug_name=document.drug_name,
                    source_type=document.source_type,
                    size_chars=len(markdown),
                )
            )

    @staticmethod
    def _spans(markdown: str, chunks: list[Chunk]) -> list[SourceChunkSpan]:
        """Convert chunk character offsets into UTF-16 spans over ``markdown``."""
        return [
            SourceChunkSpan(
                chunk_id=chunk.chunk_id,
                section_path=chunk.section_path,
                start=utf16_offset(markdown, chunk.start_char),
                end=utf16_offset(markdown, chunk.end_char),
            )
            for chunk in chunks
        ]

    def list_files(self) -> list[SourceSummary]:
        return list(self._summaries)

    def get(self, file_name: str) -> tuple[SourceDocument, str]:
        if not _FILE_RE.match(file_name) or file_name not in self._documents:
            raise NotFoundError(f"Unknown source file: {file_name!r}.")
        document = self._documents[file_name]
        return document, _etag(document.markdown)
