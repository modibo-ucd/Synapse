"""Stage 5: assemble the final answer in code from the reviewed draft."""

from __future__ import annotations

from app.agent.review import cited_text_for, missing_numbers
from app.agent.tools.base import ToolResult
from app.core.constants import MEDICAL_DISCLAIMER
from app.schemas.domain import (
    AnswerAssembly,
    Citation,
    Claim,
    Draft,
    Evidence,
    EvidenceChunk,
    Review,
)

OUT_OF_SCOPE_MESSAGE = (
    "This question is outside the scope of this pharmacology research assistant, which "
    "answers questions grounded in drug labels and consumer medication documents."
)


class Answerer:
    """Assembles the final answer (no extra LLM call)."""

    def __init__(self, disclaimer: str = MEDICAL_DISCLAIMER) -> None:
        self._disclaimer = disclaimer

    async def run(
        self, draft: Draft, review: Review, evidence: Evidence, tool_results: list[ToolResult]
    ) -> AnswerAssembly:
        if review.verdict == "insufficient_evidence":
            return self._insufficient()

        kept = [
            claim for claim in draft.claims if self._supported(claim, evidence, tool_results)
        ]
        cited_chunks = self._cited_chunks(kept, evidence)
        chunk_id_to_citation = {
            chunk.chunk_id: f"S{index}" for index, chunk in enumerate(cited_chunks, start=1)
        }
        citations = [
            Citation(
                id=f"S{index}",
                source_file=chunk.source_file,
                section=chunk.section,
                chunk_id=chunk.chunk_id,
                excerpt=self._excerpt(chunk.text),
            )
            for index, chunk in enumerate(cited_chunks, start=1)
        ]

        lines = [f"- {claim.text}{self._markers(claim, chunk_id_to_citation)}" for claim in kept]
        if not lines:
            lines = [
                "The retrieved evidence and tools do not contain enough information to answer."
            ]
        source_lines = "\n".join(
            f"{index}. {chunk.source_file} — {chunk.section}"
            for index, chunk in enumerate(cited_chunks, start=1)
        ) or "None."
        answer = (
            "\n".join(lines)
            + f"\n\n## Sources\n\n{source_lines}\n\n"
            + self._review_notes(review)
            + self._disclaimer
        )

        return AnswerAssembly(
            answer=answer,
            sources=sorted({chunk.source_file for chunk in cited_chunks}),
            citations=citations,
            disclaimer=self._disclaimer,
        )

    def run_out_of_scope(self) -> AnswerAssembly:
        answer = f"{OUT_OF_SCOPE_MESSAGE}\n\n## Sources\n\nNone.\n\n{self._disclaimer}"
        return AnswerAssembly(answer=answer, sources=[], citations=[], disclaimer=self._disclaimer)

    def _insufficient(self) -> AnswerAssembly:
        answer = (
            "Insufficient evidence in the corpus to answer this question."
            f"\n\n## Sources\n\nNone.\n\n{self._disclaimer}"
        )
        return AnswerAssembly(answer=answer, sources=[], citations=[], disclaimer=self._disclaimer)

    @staticmethod
    def _supported(claim: Claim, evidence: Evidence, tool_results: list[ToolResult]) -> bool:
        has_reference = any(
            chunk.chunk_id in claim.evidence_ids for chunk in evidence.chunks
        ) or any(result.tool_result_id in claim.tool_result_ids for result in tool_results)
        if not has_reference:
            return False
        cited = cited_text_for(claim, evidence, tool_results)
        return not missing_numbers(claim.text, cited)

    @staticmethod
    def _cited_chunks(kept: list[Claim], evidence: Evidence) -> list[EvidenceChunk]:
        by_id = {chunk.chunk_id: chunk for chunk in evidence.chunks}
        ordered: list[EvidenceChunk] = []
        seen: set[str] = set()
        for claim in kept:
            for chunk_id in claim.evidence_ids:
                chunk = by_id.get(chunk_id)
                if chunk is not None and chunk.chunk_id not in seen:
                    seen.add(chunk.chunk_id)
                    ordered.append(chunk)
        return ordered

    @staticmethod
    def _markers(claim: Claim, chunk_id_to_citation: dict[str, str]) -> str:
        ids = [
            chunk_id_to_citation[chunk_id]
            for chunk_id in claim.evidence_ids
            if chunk_id in chunk_id_to_citation
        ]
        if not ids:
            return ""
        return " [" + "][".join(ids) + "]"

    @staticmethod
    def _excerpt(text: str, limit: int = 160) -> str:
        return text if len(text) <= limit else text[:limit].rstrip() + "…"

    @staticmethod
    def _review_notes(review: Review) -> str:
        if not review.ambiguity_flags:
            return ""
        return "### Review notes\n" + "\n".join(
            f"- {flag}" for flag in review.ambiguity_flags
        ) + "\n\n"
