"""Corpus loading: read .md files and derive document metadata.

Every drug file is named ``<source_type>-<drug_name>.md`` where ``source_type`` is
``dailymed`` or ``medlineplus``. ``GLOSSARY.md`` is parsed into glossary entries
(see :mod:`app.retrieval.glossary`) and is never treated as a document.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import cast

from app.core.errors import ConfigurationError
from app.retrieval.glossary import parse_glossary
from app.schemas.domain import CorpusDocument, GlossaryEntry, SourceType

_GLOSSARY_FILE = "GLOSSARY.md"
_FILE_RE = re.compile(r"^(dailymed|medlineplus)-(.+)\.md$")


def _parse_filename(name: str) -> tuple[SourceType, str]:
    """Derive (source_type, drug_name) from a corpus file name."""
    match = _FILE_RE.match(name)
    if match is None:
        raise ConfigurationError(
            f"Unrecognized corpus file name: {name!r}. Expected 'dailymed-<drug>.md' "
            "or 'medlineplus-<drug>.md'."
        )
    return cast(SourceType, match.group(1)), match.group(2)


def _read_text(path: Path) -> str:
    """Read a file, strip a BOM if present and normalize line endings."""
    text = path.read_text(encoding="utf-8")
    if text.startswith("\ufeff"):
        text = text[1:]
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _extract_title(raw_text: str, drug_name: str, source_type: SourceType) -> str:
    """Return the first level-1 heading, falling back to a synthetic title."""
    for line in raw_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return f"{drug_name} ({source_type})"


def load_documents(corpus_dir: Path) -> list[CorpusDocument]:
    """Load every drug .md file in corpus_dir (GLOSSARY.md is handled separately)."""
    if not corpus_dir.is_dir():
        return []
    documents: list[CorpusDocument] = []
    for path in sorted(corpus_dir.glob("*.md")):
        if path.name == _GLOSSARY_FILE:
            continue
        source_type, drug_name = _parse_filename(path.name)
        raw_text = _read_text(path)
        documents.append(
            CorpusDocument(
                source_file=path.name,
                drug_name=drug_name,
                source_type=source_type,
                title=_extract_title(raw_text, drug_name, source_type),
                raw_text=raw_text,
            )
        )
    return documents


def load_glossary(corpus_dir: Path) -> list[GlossaryEntry]:
    """Parse GLOSSARY.md into glossary entries; empty when the file is absent."""
    path = corpus_dir / _GLOSSARY_FILE
    if not path.is_file():
        return []
    return parse_glossary(_read_text(path))
