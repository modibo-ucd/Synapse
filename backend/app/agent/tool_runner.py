"""Stage 3: run model-chosen tools and synthesize a grounded Draft."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from app.agent.prompts.draft import DRAFT_SYSTEM_PROMPT
from app.agent.prompts.tools import TOOLS_SYSTEM_PROMPT
from app.agent.tools.base import ToolRegistry, ToolResult
from app.core.constants import MAX_TOOL_CALLS, TOOL_TIMEOUT_S
from app.providers.protocols import LLMClient, Messages
from app.schemas.domain import Claim, Draft, Evidence, Plan

_EVIDENCE_START = "<<<BEGIN EVIDENCE>>>"
_EVIDENCE_END = "<<<END EVIDENCE>>>"


def clean_draft(
    draft: Draft, evidence_ids: set[str], tool_result_ids: set[str]
) -> tuple[Draft, bool]:
    """Drop invalid references and unreferenced claims; report whether anything changed."""
    cleaned: list[Claim] = []
    changed = False
    for claim in draft.claims:
        ev = [eid for eid in claim.evidence_ids if eid in evidence_ids]
        tr = [tid for tid in claim.tool_result_ids if tid in tool_result_ids]
        if not ev and not tr:
            changed = True
            continue
        if ev != claim.evidence_ids or tr != claim.tool_result_ids:
            changed = True
        cleaned.append(Claim(text=claim.text, evidence_ids=ev, tool_result_ids=tr))
    return Draft(claims=cleaned, markdown=draft.markdown), changed


def _draft_repair_message() -> str:
    return (
        "Your previous draft had claims with missing or invalid references. Each claim "
        "must reference at least one valid evidence id or tool result id. Respond again "
        "with a corrected Draft JSON object."
    )


class ToolRunner:
    """Runs Stage 3: bounded tool calling followed by draft synthesis."""

    def __init__(
        self,
        llm: LLMClient,
        registry: ToolRegistry,
        *,
        max_tool_calls: int = MAX_TOOL_CALLS,
        tool_timeout_s: float = TOOL_TIMEOUT_S,
    ) -> None:
        self._llm = llm
        self._registry = registry
        self._max_tool_calls = max_tool_calls
        self._tool_timeout_s = tool_timeout_s

    async def run(self, plan: Plan, evidence: Evidence) -> Draft:
        messages: Messages = [
            {"role": "system", "content": TOOLS_SYSTEM_PROMPT},
            {"role": "user", "content": self._build_user_message(plan, evidence)},
        ]
        tool_specs = self._registry.specs()
        tool_result_ids: set[str] = set()
        total_calls = 0

        while total_calls < self._max_tool_calls:
            result = await self._llm.chat_with_tools(messages, tool_specs)
            if not result.tool_calls:
                break

            assistant_calls: list[dict[str, Any]] = []
            coroutines = []
            for index, call in enumerate(result.tool_calls):
                call_id = f"call_{total_calls}_{index}"
                assistant_calls.append(
                    {
                        "id": call_id,
                        "type": "function",
                        "function": {
                            "name": call.name,
                            "arguments": json.dumps(call.arguments),
                        },
                    }
                )
                coroutines.append(
                    self._registry.execute(
                        call.name,
                        call.arguments,
                        tool_result_id=f"t{total_calls + index}",
                        timeout=self._tool_timeout_s,
                    )
                )
            messages.append(
                {
                    "role": "assistant",
                    "content": result.content,
                    "tool_calls": assistant_calls,
                }
            )
            executed: list[ToolResult] = await asyncio.gather(*coroutines)
            for index, tool_result in enumerate(executed):
                tool_result_ids.add(tool_result.tool_result_id)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": f"call_{total_calls}_{index}",
                        "content": tool_result.model_dump_json(),
                    }
                )
            total_calls += len(executed)

        messages.append({"role": "user", "content": DRAFT_SYSTEM_PROMPT})
        draft = (await self._llm.generate_structured(messages, Draft)).parsed

        evidence_ids = {chunk.chunk_id for chunk in evidence.chunks}
        cleaned, changed = clean_draft(draft, evidence_ids, tool_result_ids)
        if changed:
            messages.append({"role": "user", "content": _draft_repair_message()})
            repaired = (await self._llm.generate_structured(messages, Draft)).parsed
            cleaned, _ = clean_draft(repaired, evidence_ids, tool_result_ids)
        return cleaned

    def _build_user_message(self, plan: Plan, evidence: Evidence) -> str:
        parts: list[str] = []
        if plan.sub_goals:
            lines = [f"{i + 1}. {sg.question}" for i, sg in enumerate(plan.sub_goals)]
            parts.append("Sub-questions:\n" + "\n".join(lines))
        parts.append(
            f"{_EVIDENCE_START}\n{self._format_evidence(evidence)}\n{_EVIDENCE_END}"
        )
        return "\n\n".join(parts)

    @staticmethod
    def _format_evidence(evidence: Evidence) -> str:
        if not evidence.chunks:
            return "(no evidence retrieved)"
        blocks = [
            f"[EVIDENCE ID: {chunk.chunk_id}] {chunk.source_file} | {chunk.section_path}\n"
            f"{chunk.text}"
            for chunk in evidence.chunks
        ]
        return "\n\n".join(blocks)
