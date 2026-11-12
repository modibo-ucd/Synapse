"""glossary_lookup tool: normalized match with fuzzy fallback over the glossary."""

from __future__ import annotations

import difflib

from pydantic import BaseModel, ConfigDict

from app.agent.tools.base import Tool
from app.schemas.domain import GlossaryEntry


class GlossaryLookupArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    term: str


class GlossaryLookupResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    found: bool
    matched_term: str = ""
    term: str = ""
    definition: str = ""
    category: str = ""
    source: str = "GLOSSARY.md"


class GlossaryLookupTool(Tool):
    name = "glossary_lookup"
    description = "Look up a pharmacology term or abbreviation in the glossary."
    args_model = GlossaryLookupArgs

    def __init__(self, entries: list[GlossaryEntry]) -> None:
        self._index: dict[str, GlossaryEntry] = {}
        for entry in entries:
            self._index[entry.term.lower()] = entry
            for alias in entry.aliases:
                self._index[alias.lower()] = entry
        self._keys = list(self._index)

    async def run(self, args: BaseModel) -> BaseModel:
        assert isinstance(args, GlossaryLookupArgs)
        normalized = args.term.strip().lower()
        matched = normalized
        entry = self._index.get(normalized)
        if entry is None and self._keys:
            close = difflib.get_close_matches(normalized, self._keys, n=1, cutoff=0.6)
            if close:
                matched = close[0]
                entry = self._index[matched]
        if entry is None:
            return GlossaryLookupResult(found=False)
        return GlossaryLookupResult(
            found=True,
            matched_term=matched,
            term=entry.term,
            definition=entry.definition,
            category=entry.category,
            source="GLOSSARY.md",
        )
