"""Stage 5: assemble the final answer in code from the reviewed draft."""

from __future__ import annotations

from app.agent.review import cited_text_for, extract_numbers, missing_numbers
from app.agent.tools.base import ToolResult
from app.core.constants import MEDICAL_DISCLAIMER
from app.core.egfr import extract_egfr_thresholds
from app.schemas.domain import (
    AnswerAssembly,
    Citation,
    Claim,
    Comparison,
    ComparisonCell,
    ComparisonRow,
    Draft,
    EgfrThreshold,
    EgfrWidget,
    Evidence,
    EvidenceChunk,
    Plan,
    Review,
)

OUT_OF_SCOPE_MESSAGE = (
    "This question is outside the scope of this pharmacology research assistant, which "
    "answers questions grounded in drug labels and consumer medication documents."
)

# (attribute, section-substrings) used to build the multi-drug comparison matrix.
_ATTRIBUTES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("contraindications", ("CONTRAINDICATIONS",)),
    ("boxed_warning", ("WARNING:", "BOXED WARNING")),
    ("major_risks", ("WARNINGS AND PRECAUTIONS",)),
    ("monitoring", ("MONITORING", "DOSAGE AND ADMINISTRATION", "CLINICAL PHARMACOLOGY")),
    ("notable_interactions", ("INTERACTIONS",)),
)


class Answerer:
    """Assembles the final answer (no extra LLM call)."""

    def __init__(self, disclaimer: str = MEDICAL_DISCLAIMER) -> None:
        self._disclaimer = disclaimer

    async def run(
        self,
        draft: Draft,
        review: Review,
        evidence: Evidence,
        tool_results: list[ToolResult],
        question: str = "",
        plan: Plan | None = None,
    ) -> AnswerAssembly:
        if review.verdict == "insufficient_evidence":
            return self._insufficient()

        allowed = extract_numbers(question)
        kept = [
            claim for claim in draft.claims
            if self._supported(claim, evidence, tool_results, allowed)
        ]

        cited_chunks = self._cited_chunks(kept, evidence)
        cited_tools = self._cited_tools(kept, tool_results)
        chunk_markers = {
            chunk.chunk_id: f"S{index}" for index, chunk in enumerate(cited_chunks, start=1)
        }
        tool_markers = {
            result.tool_result_id: f"S{len(cited_chunks) + index}"
            for index, result in enumerate(cited_tools, start=1)
        }
        comparison = self._build_comparison(plan, cited_chunks, chunk_markers)
        widgets = self._build_widgets(cited_chunks, chunk_markers)

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
        citations += [
            self._tool_citation(f"S{len(cited_chunks) + index}", result)
            for index, result in enumerate(cited_tools, start=1)
        ]

        lines = [
            f"- {claim.text}{self._markers(claim, chunk_markers, tool_markers)}"
            for claim in kept
        ]
        if not lines:
            lines = [
                "The retrieved evidence and tools do not contain enough information to answer."
            ]
        source_files = sorted(
            {chunk.source_file for chunk in cited_chunks}
            | {self._tool_source_file(result) for result in cited_tools}
        )
        source_lines = "\n".join(
            f"{index}. {source_file}" for index, source_file in enumerate(source_files, start=1)
        ) or "None."
        answer = (
            "\n".join(lines)
            + f"\n\n## Sources\n\n{source_lines}\n\n"
            + self._review_notes(review)
            + self._disclaimer
        )

        return AnswerAssembly(
            answer=answer,
            sources=source_files,
            citations=citations,
            disclaimer=self._disclaimer,
            comparison=comparison,
            widgets=widgets,
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
    def _supported(
        claim: Claim,
        evidence: Evidence,
        tool_results: list[ToolResult],
        allowed: set[str],
    ) -> bool:
        has_reference = any(
            chunk.chunk_id in claim.evidence_ids for chunk in evidence.chunks
        ) or any(result.tool_result_id in claim.tool_result_ids for result in tool_results)
        if not has_reference:
            return False
        cited = cited_text_for(claim, evidence, tool_results)
        return not missing_numbers(claim.text, cited, allowed)

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
    def _cited_tools(kept: list[Claim], tool_results: list[ToolResult]) -> list[ToolResult]:
        """Return the tool results referenced by claims that also name a source file."""
        by_id = {result.tool_result_id: result for result in tool_results}
        ordered: list[ToolResult] = []
        seen: set[str] = set()
        for claim in kept:
            for tool_id in claim.tool_result_ids:
                result = by_id.get(tool_id)
                if result is not None and result.tool_result_id not in seen:
                    if Answerer._tool_source_file(result):
                        seen.add(result.tool_result_id)
                        ordered.append(result)
        return ordered

    @staticmethod
    def _tool_source_file(result: ToolResult) -> str:
        output = result.output or {}
        return str(output.get("source_file", ""))

    @staticmethod
    def _tool_citation(citation_id: str, result: ToolResult) -> Citation:
        output = result.output or {}
        text = str(output.get("text") or output.get("supporting_passage") or "")
        section = str(output.get("section") or output.get("heading_path") or "")
        return Citation(
            id=citation_id,
            source_file=Answerer._tool_source_file(result),
            section=section,
            chunk_id=result.tool_result_id,
            excerpt=Answerer._excerpt(text),
        )

    @staticmethod
    def _markers(
        claim: Claim, chunk_markers: dict[str, str], tool_markers: dict[str, str]
    ) -> str:
        ids = [
            chunk_markers[chunk_id]
            for chunk_id in claim.evidence_ids
            if chunk_id in chunk_markers
        ]
        ids += [
            tool_markers[tool_id]
            for tool_id in claim.tool_result_ids
            if tool_id in tool_markers
        ]
        if not ids:
            return ""
        return " [" + "][".join(ids) + "]"

    @staticmethod
    def _excerpt(text: str, limit: int = 500) -> str:
        """Return ``text`` truncated to at most ``limit`` chars on a sentence boundary."""
        text = text.strip()
        if len(text) <= limit:
            return text
        window = text[:limit]
        cut = -1
        for boundary in (". ", ".\n", "! ", "!\n", "? ", "?\n"):
            position = window.rfind(boundary)
            if position > cut:
                cut = position
        if cut > 0:
            return window[: cut + 1].rstrip() + "…"
        space = window.rfind(" ")
        if space > 0:
            return window[:space].rstrip() + "…"
        return window.rstrip() + "…"

    @staticmethod
    def _build_comparison(
        plan: Plan | None,
        cited_chunks: list[EvidenceChunk],
        chunk_markers: dict[str, str],
    ) -> Comparison | None:
        """Build the comparison matrix for multi_hop plans spanning 2+ drugs."""
        if plan is None or plan.complexity != "multi_hop":
            return None
        drugs = sorted({chunk.drug_name for chunk in cited_chunks})
        if len(drugs) < 2:
            return None
        rows = [
            ComparisonRow(
                attribute=attribute,
                values={
                    drug: Answerer._comparison_cell(drug, keywords, cited_chunks, chunk_markers)
                    for drug in drugs
                },
            )
            for attribute, keywords in _ATTRIBUTES
        ]
        return Comparison(drugs=drugs, rows=rows)

    @staticmethod
    def _comparison_cell(
        drug: str,
        keywords: tuple[str, ...],
        cited_chunks: list[EvidenceChunk],
        chunk_markers: dict[str, str],
    ) -> ComparisonCell:
        matches = [
            chunk
            for chunk in cited_chunks
            if chunk.drug_name == drug
            and any(keyword in chunk.section.upper() for keyword in keywords)
        ]
        if not matches:
            return ComparisonCell(text="Not stated in sources", citation_ids=[])
        text = Answerer._excerpt(" ".join(chunk.text for chunk in matches), limit=240)
        citation_ids = [
            chunk_markers[chunk.chunk_id]
            for chunk in matches
            if chunk.chunk_id in chunk_markers
        ]
        return ComparisonCell(text=text, citation_ids=citation_ids)

    @staticmethod
    def _build_widgets(
        cited_chunks: list[EvidenceChunk], chunk_markers: dict[str, str]
    ) -> list[EgfrWidget] | None:
        """Build an eGFR widget when the cited evidence mentions renal thresholds."""
        by_value: dict[float, list[str]] = {}
        for chunk in cited_chunks:
            marker = chunk_markers.get(chunk.chunk_id)
            if marker is None:
                continue
            for value in extract_egfr_thresholds(chunk.text):
                by_value.setdefault(value, []).append(marker)

        if not by_value:
            return None
        thresholds = [
            EgfrThreshold(value=value, citation_ids=sorted(set(ids)))
            for value, ids in sorted(by_value.items())
        ]
        return [EgfrWidget(thresholds=thresholds)]

    @staticmethod
    def _review_notes(review: Review) -> str:
        if not review.ambiguity_flags:
            return ""
        return "### Review notes\n" + "\n".join(
            f"- {flag}" for flag in review.ambiguity_flags
        ) + "\n\n"
