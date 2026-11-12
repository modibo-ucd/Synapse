"""CLI to inspect retrieval quality: ``python -m app.retrieval.debug "question"``.

Builds the index (reusing the on-disk embedding cache), forms a single sub-goal
plan for the question (detecting corpus drugs for the drug-coverage rule), and
prints the top fused chunks with ranks, files and sections. This is a dev tool:
the graded pipeline builds its plan from the LLM in Task 5.
"""

from __future__ import annotations

import asyncio
import sys

from app.core.config import get_settings
from app.providers import openai as openai_providers
from app.retrieval.index_manager import IndexManager
from app.schemas.domain import Plan, SubGoal


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print('usage: python -m app.retrieval.debug "question"')
        return
    question = " ".join(args)
    asyncio.run(_run(question))


async def _run(question: str) -> None:
    settings = get_settings()
    manager = IndexManager(settings, openai_providers.build_embedding_provider(settings))
    await manager.await_ready(timeout=600.0)
    retriever = manager.retriever
    if retriever is None:
        print("index unavailable")
        return

    entities = _detect_drugs(question, manager.drug_names)
    plan = Plan(
        complexity="multi_hop" if len(entities) > 1 else "simple",
        in_scope=True,
        sub_goals=[SubGoal(id="q", question=question, intent="", entities=entities)],
    )
    evidence = await retriever.run(plan)

    print(f"retrieval_mode={evidence.retrieval_mode}  chunks={len(evidence.chunks)}")
    for chunk in evidence.chunks:
        dense = chunk.dense_rank if chunk.dense_rank is not None else "-"
        bm25 = chunk.bm25_rank if chunk.bm25_rank is not None else "-"
        header = f"[d{dense} b{bm25} s{chunk.fused_score:.4f}]"
        print(f"{header} {chunk.source_file} | {chunk.section_path}")
        print(f"    {' '.join(chunk.text.split())[:160]}")


def _detect_drugs(question: str, drugs: set[str]) -> list[str]:
    lowered = question.lower()
    return sorted(drug for drug in drugs if drug in lowered)


if __name__ == "__main__":
    main()
