"""label_section_lookup tool: return a label section by heading path."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.agent.tools.base import Tool
from app.schemas.domain import Chunk

_SYNONYMS: dict[str, str] = {
    "boxed warning": "warning",
    "black box": "warning",
    "dosage": "dosage and administration",
    "dosing": "dosage and administration",
    "side effects": "adverse reactions",
}


class LabelSectionArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    drug: str
    section: str


class LabelSectionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    found: bool
    drug: str = ""
    section: str = ""
    source_file: str = ""
    heading_path: str = ""
    text: str = ""


class LabelSectionLookupTool(Tool):
    name = "label_section_lookup"
    description = (
        "Return a drug label section (e.g. Boxed Warning, Contraindications, Dosage "
        "and Administration, Drug Interactions, renal impairment) by heading path."
    )
    args_model = LabelSectionArgs

    def __init__(self, chunks: list[Chunk]) -> None:
        self._chunks = chunks

    async def run(self, args: BaseModel) -> BaseModel:
        assert isinstance(args, LabelSectionArgs)
        drug = args.drug.strip().lower()
        needles = _needles(args.section)
        for chunk in self._chunks:
            if chunk.drug_name != drug:
                continue
            path = chunk.section_path.lower()
            if any(needle in path for needle in needles):
                return LabelSectionResult(
                    found=True,
                    drug=drug,
                    section=args.section.strip(),
                    source_file=chunk.source_file,
                    heading_path=chunk.section_path,
                    text=chunk.text,
                )
        return LabelSectionResult(found=False)


def _needles(section: str) -> list[str]:
    section = section.strip().lower()
    needles = {section}
    for key, value in _SYNONYMS.items():
        if key in section:
            needles.add(value)
    return list(needles)
