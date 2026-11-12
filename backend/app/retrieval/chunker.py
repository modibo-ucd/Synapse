"""Structure-aware chunking of corpus documents.

Splits each document on Markdown headings and keeps the full heading path
(``Drug > Section > Subsection``) on every chunk. Table blocks and the Boxed
Warning / Contraindications / Dosage sections are never split mid-way. Oversized
sections are split only at paragraph or table-row boundaries, with a small
overlap and the table header row repeated on each continuation chunk.

Design notes
------------
* A "block" is a run of non-blank lines. A block containing any ``|`` character
  is treated as a table and kept atomic (the corpus prose contains no pipes).
* Tables in this corpus are heterogeneous (leading-pipe rows, plain ``a | b``
  rows and ``Label: | value`` rows), but their rows are always contiguous, so the
  blank-line block split already keeps them together.
* A single paragraph or table row larger than ``max_tokens`` cannot be split
  without violating the paragraph/row boundary rule, so it is emitted whole.
"""

from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass

from app.core.constants import CHARS_PER_TOKEN, CHUNK_MAX_TOKENS, CHUNK_OVERLAP_TOKENS
from app.schemas.domain import Chunk, CorpusDocument

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_WARNING_RE = re.compile(r"^(?:IMPORTANT )?WARNING\b", re.IGNORECASE)


def count_tokens(text: str, chars_per_token: float = CHARS_PER_TOKEN) -> int:
    """Approximate token count by character length (configurable)."""
    if chars_per_token <= 0:
        raise ValueError("chars_per_token must be positive")
    return max(1, math.ceil(len(text) / chars_per_token))


@dataclass(frozen=True)
class _Block:
    """An atomic run of non-blank lines: either prose or a table."""

    lines: tuple[str, ...]
    is_table: bool

    @property
    def text(self) -> str:
        return "\n".join(self.lines)


@dataclass(frozen=True)
class _Unit:
    """A minimal chunk-able piece: a block, or a table split at row boundaries."""

    text: str
    tokens: int


@dataclass
class _Section:
    """Content under one heading, with its full heading path."""

    path: tuple[str, ...]
    heading: str
    lines: list[str]


def _make_block(lines: list[str]) -> _Block:
    return _Block(lines=tuple(lines), is_table=any("|" in line for line in lines))


def _split_blocks(lines: list[str]) -> list[_Block]:
    blocks: list[_Block] = []
    current: list[str] = []
    for line in lines:
        if line.strip() == "":
            if current:
                blocks.append(_make_block(current))
                current = []
        else:
            current.append(line)
    if current:
        blocks.append(_make_block(current))
    return blocks


def _parse_sections(lines: list[str], doc: CorpusDocument) -> list[_Section]:
    """Split lines into sections keyed by level-2+ headings.

    Level-1 headings (the document title) and the preamble under them (the
    ``Source:`` line) are not chunked; the drug name becomes the path root.
    """
    sections: list[_Section] = []
    stack: list[tuple[int, str]] = []
    path: tuple[str, ...] | None = None
    heading: str | None = None
    content: list[str] = []

    def flush() -> None:
        nonlocal path, heading, content
        if path is not None:
            sections.append(_Section(path=path, heading=heading or "", lines=content))
        path = None
        heading = None
        content = []

    for line in lines:
        match = _HEADING_RE.match(line)
        if match is None:
            if path is not None:
                content.append(line)
            continue
        level = len(match.group(1))
        text = match.group(2).strip()
        if level == 1:
            stack.clear()
            flush()
            continue
        flush()
        while stack and stack[-1][0] >= level:
            stack.pop()
        stack.append((level, text))
        heading = text
        path = (doc.drug_name,) + tuple(t for _, t in stack)
        content = []

    flush()
    return sections


def _is_protected(path: tuple[str, ...]) -> bool:
    """True when the section must never be split across chunks."""
    for heading in path:
        if _WARNING_RE.match(heading.strip()):
            return True
        upper = heading.upper()
        if "CONTRAINDICATIONS" in upper or "DOSAGE AND ADMINISTRATION" in upper:
            return True
    return False


def _split_table(block: _Block, *, max_tokens: int, chars_per_token: float) -> list[_Unit]:
    """Split an oversized table at row boundaries, repeating the header row."""
    header = next((line for line in block.lines if "|" in line), "")
    rows = [line for line in block.lines if line != header]
    header_tokens = count_tokens(header, chars_per_token)
    units: list[_Unit] = []
    current: list[str] = []
    current_tokens = header_tokens
    for row in rows:
        row_tokens = count_tokens(row, chars_per_token)
        if current and current_tokens + row_tokens > max_tokens:
            units.append(_Unit(text="\n".join([header, *current]), tokens=current_tokens))
            current = []
            current_tokens = header_tokens
        current.append(row)
        current_tokens += row_tokens
    if current:
        units.append(_Unit(text="\n".join([header, *current]), tokens=current_tokens))
    return units


def _to_units(blocks: list[_Block], *, max_tokens: int, chars_per_token: float) -> list[_Unit]:
    units: list[_Unit] = []
    for block in blocks:
        tokens = count_tokens(block.text, chars_per_token)
        if not block.is_table or tokens <= max_tokens:
            units.append(_Unit(text=block.text, tokens=tokens))
        else:
            units.extend(
                _split_table(block, max_tokens=max_tokens, chars_per_token=chars_per_token)
            )
    return units


def _overlap_prefix(group: list[_Unit], overlap_tokens: int) -> tuple[list[_Unit], int]:
    """Return a trailing suffix of ``group`` totalling at most ``overlap_tokens``."""
    if overlap_tokens <= 0:
        return [], 0
    picked: list[_Unit] = []
    total = 0
    for unit in reversed(group):
        if total + unit.tokens > overlap_tokens:
            break
        picked.append(unit)
        total += unit.tokens
    picked.reverse()
    return picked, total


def _pack_units(units: list[_Unit], *, max_tokens: int, overlap_tokens: int) -> list[list[_Unit]]:
    """Greedily pack units into chunks, overlapping a small tail of the previous chunk."""
    groups: list[list[_Unit]] = []
    current: list[_Unit] = []
    current_tokens = 0
    previous: list[_Unit] = []

    for unit in units:
        if unit.tokens > max_tokens:
            if current:
                groups.append(current)
                current = []
                current_tokens = 0
            groups.append([unit])
            previous = [unit]
            continue

        if current and current_tokens + unit.tokens > max_tokens:
            groups.append(current)
            previous = current
            current = []
            current_tokens = 0
            overlap, overlap_tokens_total = _overlap_prefix(previous, overlap_tokens)
            if overlap_tokens_total + unit.tokens <= max_tokens:
                current = overlap
                current_tokens = overlap_tokens_total

        current.append(unit)
        current_tokens += unit.tokens

    if current:
        groups.append(current)
    return groups


def _build_chunk(
    doc: CorpusDocument,
    *,
    section_path: str,
    section: str,
    text: str,
    index: int,
    chars_per_token: float,
) -> Chunk:
    digest = hashlib.sha256(f"{doc.source_file}|{section_path}|{index}".encode())
    return Chunk(
        chunk_id=digest.hexdigest()[:16],
        source_file=doc.source_file,
        drug_name=doc.drug_name,
        source_type=doc.source_type,
        section_path=section_path,
        section=section,
        text=text,
        embedding_text=f"{doc.drug_name} ({doc.source_type}) {section_path}\n{text}",
        index=index,
        token_count=count_tokens(text, chars_per_token),
    )


def _chunk_section(
    doc: CorpusDocument,
    section: _Section,
    *,
    max_tokens: int,
    overlap_tokens: int,
    chars_per_token: float,
) -> list[Chunk]:
    blocks = _split_blocks(section.lines)
    if not blocks:
        return []
    section_path = " > ".join(section.path)
    total_tokens = sum(count_tokens(block.text, chars_per_token) for block in blocks)
    if _is_protected(section.path) or total_tokens <= max_tokens:
        text = "\n\n".join(block.text for block in blocks).strip()
        return [
            _build_chunk(
                doc,
                section_path=section_path,
                section=section.heading,
                text=text,
                index=0,
                chars_per_token=chars_per_token,
            )
        ]

    units = _to_units(blocks, max_tokens=max_tokens, chars_per_token=chars_per_token)
    groups = _pack_units(units, max_tokens=max_tokens, overlap_tokens=overlap_tokens)
    return [
        _build_chunk(
            doc,
            section_path=section_path,
            section=section.heading,
            text="\n\n".join(unit.text for unit in group).strip(),
            index=index,
            chars_per_token=chars_per_token,
        )
        for index, group in enumerate(groups)
    ]


def chunk_document(
    doc: CorpusDocument,
    *,
    max_tokens: int = CHUNK_MAX_TOKENS,
    overlap_tokens: int = CHUNK_OVERLAP_TOKENS,
    chars_per_token: float = CHARS_PER_TOKEN,
) -> list[Chunk]:
    """Chunk a single document into structure-aware chunks."""
    lines = [line.rstrip() for line in doc.raw_text.splitlines()]
    sections = _parse_sections(lines, doc)
    if not sections:
        text = "\n\n".join(block.text for block in _split_blocks(lines)).strip()
        if not text:
            return []
        return [
            _build_chunk(
                doc,
                section_path=doc.drug_name,
                section="",
                text=text,
                index=0,
                chars_per_token=chars_per_token,
            )
        ]

    chunks: list[Chunk] = []
    for section in sections:
        chunks.extend(
            _chunk_section(
                doc,
                section,
                max_tokens=max_tokens,
                overlap_tokens=overlap_tokens,
                chars_per_token=chars_per_token,
            )
        )
    return chunks


def chunk_documents(
    documents: list[CorpusDocument],
    *,
    max_tokens: int = CHUNK_MAX_TOKENS,
    overlap_tokens: int = CHUNK_OVERLAP_TOKENS,
    chars_per_token: float = CHARS_PER_TOKEN,
) -> list[Chunk]:
    """Chunk every document and flatten the result."""
    chunks: list[Chunk] = []
    for document in documents:
        chunks.extend(
            chunk_document(
                document,
                max_tokens=max_tokens,
                overlap_tokens=overlap_tokens,
                chars_per_token=chars_per_token,
            )
        )
    return chunks


