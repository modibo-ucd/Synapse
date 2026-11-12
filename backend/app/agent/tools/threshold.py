"""threshold_check tool: conservative numeric threshold extraction from label text."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.agent.tools.base import Tool
from app.schemas.domain import Chunk

Verdict = Literal[
    "contraindicated", "not_recommended_to_start", "caution", "within_range", "unknown"
]

_BELOW_RE = re.compile(r"(?:below|less than|under)\s*(\d+(?:\.\d+)?)")
_BETWEEN_RE = re.compile(r"between\s*(\d+(?:\.\d+)?)\s*(?:and|to)\s*(\d+(?:\.\d+)?)")
_RANGE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:to|and)\s*(\d+(?:\.\d+)?)")


class ThresholdCheckArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    drug: str
    parameter: str
    value: float


class ThresholdCheckResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    found: bool
    drug: str = ""
    parameter: str = ""
    value: float = 0.0
    verdict: Verdict = "unknown"
    supporting_passage: str = ""
    source_file: str = ""


def extract_threshold(text: str, parameter: str, value: float) -> tuple[Verdict, str]:
    """Conservatively extract a numeric threshold verdict from label text.

    Returns ``(verdict, supporting_passage)``. ``unknown`` is returned unless a
    threshold can be parsed with certainty. Only the provided text is used — never
    outside knowledge.
    """
    lowered = text.lower()
    if parameter.strip().lower() not in lowered:
        return "unknown", ""

    for match in _BELOW_RE.finditer(lowered):
        threshold = float(match.group(1))
        window = lowered[max(0, match.start() - 160) : match.end() + 160]
        if ("contraindicated" in window or "discontinue" in window) and value < threshold:
            return "contraindicated", _passage(text, match.start(), match.end())

    for match in _BETWEEN_RE.finditer(lowered):
        low = float(match.group(1))
        high = float(match.group(2))
        window = lowered[max(0, match.start() - 160) : match.end() + 160]
        if "not recommended" in window and low <= value < high:
            return "not_recommended_to_start", _passage(text, match.start(), match.end())

    for match in _RANGE_RE.finditer(lowered):
        low = float(match.group(1))
        high = float(match.group(2))
        window = lowered[max(0, match.start() - 80) : match.end() + 80]
        if (
            "target" in window or "range" in window or "desired" in window
        ) and low <= value <= high:
            return "within_range", _passage(text, match.start(), match.end())

    if "caution" in lowered:
        index = lowered.find("caution")
        return "caution", _passage(text, index, index + 7)

    return "unknown", ""


def _passage(text: str, start: int, end: int) -> str:
    return text[max(0, start - 100) : end + 100].strip()


class ThresholdCheckTool(Tool):
    name = "threshold_check"
    description = (
        "Compare a numeric value against a conservative threshold extracted from a "
        "drug label (e.g. eGFR below 30, eGFR between 30 and 45)."
    )
    args_model = ThresholdCheckArgs

    def __init__(self, chunks: list[Chunk]) -> None:
        self._chunks = chunks

    async def run(self, args: BaseModel) -> BaseModel:
        assert isinstance(args, ThresholdCheckArgs)
        drug = args.drug.strip().lower()
        parameter = args.parameter.strip().lower()
        value = args.value
        priority: dict[Verdict, int] = {
            "contraindicated": 4,
            "not_recommended_to_start": 3,
            "within_range": 2,
            "caution": 1,
            "unknown": 0,
        }
        best: tuple[int, Verdict, str, str] = (0, "unknown", "", "")
        for chunk in self._chunks:
            if chunk.drug_name != drug:
                continue
            verdict, passage = extract_threshold(chunk.text, parameter, value)
            score = priority[verdict]
            if score > best[0]:
                best = (score, verdict, passage, chunk.source_file)
        return ThresholdCheckResult(
            found=best[0] > 0,
            drug=drug,
            parameter=parameter,
            value=value,
            verdict=best[1],
            supporting_passage=best[2],
            source_file=best[3],
        )
