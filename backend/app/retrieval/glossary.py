"""Parsing for GLOSSARY.md into structured glossary entries.

GLOSSARY.md is a list of ``- **Term**: definition.`` items grouped under ``##``
category headings. Some terms carry aliases/abbreviations in parentheses or
quotes, e.g. ``**Half-life (t½)**`` or ``**INR (International Normalized
Ratio)**``. Definitions may wrap onto indented continuation lines.
"""

from __future__ import annotations

import re

from app.schemas.domain import GlossaryEntry

_ENTRY_RE = re.compile(r"^-\s+\*\*(.+?)\*\*:\s*(.*)$")
_HEADING_RE = re.compile(r"^#{1,6}\s+(.*)$")
_PAREN_RE = re.compile(r"\(([^()]*)\)")
_QUOTE_RE = re.compile(r'"([^"]*)"')
_ALIAS_PREFIX_RE = re.compile(r"^(?:e\.g\.?|formerly|previously)\s*", re.IGNORECASE)


def _extract_aliases(bold: str) -> tuple[str, list[str]]:
    """Split a bold term into its canonical term and any aliases.

    Aliases come only from inside parentheses: quoted strings (e.g. ``previously
    "black box"``) and comma-separated parts (with an optional ``e.g.`` prefix
    dropped). Quotes outside parentheses are part of the term itself, e.g. the
    entry ``**"Highlights of Prescribing Information"**``.
    """
    aliases: list[str] = []
    for group in _PAREN_RE.findall(bold):
        for quoted in _QUOTE_RE.findall(group):
            cleaned = quoted.strip()
            if cleaned:
                aliases.append(cleaned)
        for part in group.split(","):
            cleaned = _QUOTE_RE.sub(r"\1", part).strip()
            cleaned = _ALIAS_PREFIX_RE.sub("", cleaned).strip()
            if cleaned:
                aliases.append(cleaned)

    term = _PAREN_RE.sub("", bold).strip()
    term = re.sub(r"\s{2,}", " ", term)

    seen: set[str] = set()
    unique: list[str] = []
    for alias in aliases:
        if alias not in seen:
            seen.add(alias)
            unique.append(alias)
    return term, unique


def parse_glossary(text: str) -> list[GlossaryEntry]:
    """Parse the raw GLOSSARY.md text into a list of GlossaryEntry models."""
    entries: list[GlossaryEntry] = []
    category = ""
    pending: GlossaryEntry | None = None

    def flush() -> None:
        nonlocal pending
        if pending is not None:
            entries.append(pending)
            pending = None

    for raw_line in text.splitlines():
        line = raw_line.rstrip()

        heading = _HEADING_RE.match(line)
        if heading:
            flush()
            category = heading.group(1).strip()
            continue

        entry = _ENTRY_RE.match(line)
        if entry:
            flush()
            term, aliases = _extract_aliases(entry.group(1).strip())
            pending = GlossaryEntry(
                term=term,
                aliases=aliases,
                definition=entry.group(2).strip(),
                category=category,
            )
            continue

        if pending is not None and line.strip():
            pending = GlossaryEntry(
                term=pending.term,
                aliases=pending.aliases,
                definition=f"{pending.definition} {line.strip()}".strip(),
                category=pending.category,
            )

    flush()
    return entries
