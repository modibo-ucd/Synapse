"""Stage 4: a separate reviewer LLM call plus deterministic grounding checks."""

from __future__ import annotations

import re

from app.agent.prompts.review import REVIEW_SYSTEM_PROMPT
from app.agent.tools.base import ToolResult
from app.providers.protocols import LLMClient, Messages
from app.schemas.domain import Claim, Draft, Evidence, Review, ReviewVerdict

_NUMBER_RE = re.compile(r"\d+(?:\.\d+)?")

_EVIDENCE_START = "<<<BEGIN EVIDENCE>>>"
_EVIDENCE_END = "<<<END EVIDENCE>>>"
_TOOLS_START = "<<<BEGIN TOOL OUTPUT>>>"
_TOOLS_END = "<<<END TOOL OUTPUT>>>"


def cited_text_for(claim: Claim, evidence: Evidence, tool_results: list[ToolResult]) -> str:
    """Return the concatenated text that a claim is grounded in."""
    parts: list[str] = []
    for chunk in evidence.chunks:
        if chunk.chunk_id in claim.evidence_ids:
            parts.append(chunk.text)
    for result in tool_results:
        if result.tool_result_id in claim.tool_result_ids:
            parts.append(result.model_dump_json())
    return "\n".join(parts)


def missing_numbers(claim_text: str, cited_text: str) -> list[str]:
    """Return numbers in ``claim_text`` that do not appear verbatim in ``cited_text``."""
    missing: list[str] = []
    seen: set[str] = set()
    for match in _NUMBER_RE.finditer(claim_text):
        number = match.group(0)
        if number not in cited_text and number not in seen:
            seen.add(number)
            missing.append(number)
    return missing


class Reviewer:
    """Runs the Stage 4 review: deterministic checks + a separate LLM audit."""

    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    async def run(
        self, draft: Draft, evidence: Evidence, tool_results: list[ToolResult]
    ) -> Review:
        deterministic: list[str] = []
        for index, claim in enumerate(draft.claims):
            cited = cited_text_for(claim, evidence, tool_results)
            for number in missing_numbers(claim.text, cited):
                deterministic.append(
                    f"Claim {index + 1} references number '{number}' not found in its cited text."
                )

        messages: Messages = [
            {"role": "system", "content": REVIEW_SYSTEM_PROMPT},
            {"role": "user", "content": self._audit_prompt(draft, evidence, tool_results)},
        ]
        llm_review = (await self._llm.generate_structured(messages, Review)).parsed

        unsupported = [*llm_review.unsupported_claims, *deterministic]
        ambiguities = list(llm_review.ambiguity_flags)
        verdict = self._verdict(llm_review.verdict, draft, evidence, unsupported, ambiguities)
        return Review(
            verdict=verdict,
            unsupported_claims=unsupported,
            ambiguity_flags=ambiguities,
        )

    @staticmethod
    def _verdict(
        llm_verdict: ReviewVerdict,
        draft: Draft,
        evidence: Evidence,
        unsupported: list[str],
        ambiguities: list[str],
    ) -> ReviewVerdict:
        if llm_verdict == "insufficient_evidence" or (not draft.claims and not evidence.chunks):
            return "insufficient_evidence"
        if unsupported or ambiguities:
            return "revise"
        return "pass"

    @staticmethod
    def _audit_prompt(draft: Draft, evidence: Evidence, tool_results: list[ToolResult]) -> str:
        blocks = ["Draft claims:"]
        for index, claim in enumerate(draft.claims):
            blocks.append(
                f"{index + 1}. {claim.text} "
                f"(evidence_ids={claim.evidence_ids}, tool_result_ids={claim.tool_result_ids})"
            )
        blocks.append(_EVIDENCE_START)
        for chunk in evidence.chunks:
            blocks.append(
                f"[{chunk.chunk_id}] {chunk.source_file} | {chunk.section_path}\n{chunk.text}"
            )
        blocks.append(_EVIDENCE_END)
        blocks.append(_TOOLS_START)
        for result in tool_results:
            blocks.append(f"[{result.tool_result_id}] {result.model_dump_json()}")
        blocks.append(_TOOLS_END)
        return "\n\n".join(blocks)
