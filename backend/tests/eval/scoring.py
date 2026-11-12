"""Deterministic scoring for the eval harness (pure functions, no I/O or network)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

QuestionKind = Literal["answerable", "out_of_scope", "insufficient_evidence"]

LATENCY_BUDGET_MS = 60_000


class GoldenQuestion(BaseModel):
    """One golden eval question and its expected observable outcome."""

    model_config = ConfigDict(extra="forbid")

    id: str
    question: str
    kind: QuestionKind = "answerable"
    expected_files: list[str] = Field(default_factory=list)
    must_include: list[str] = Field(default_factory=list)


class GoldenSet(BaseModel):
    """The full set of golden questions loaded from golden_questions.yaml."""

    model_config = ConfigDict(extra="forbid")

    questions: list[GoldenQuestion]


@dataclass
class QuestionResult:
    """The scored outcome for a single question (serializable for the report)."""

    id: str
    kind: QuestionKind
    passed: bool
    checks: dict[str, bool] = field(default_factory=dict)
    details: dict[str, Any] = field(default_factory=dict)


def score_question(golden: GoldenQuestion, body: dict[str, Any]) -> QuestionResult:
    """Score one API response body against its golden expectation."""
    answer = str(body.get("answer", ""))
    sources = [str(s) for s in body.get("sources", []) or []]
    disclaimer = str(body.get("disclaimer", ""))
    plan = body.get("plan") or {}
    review = body.get("review") or {}
    verdict = str(review.get("verdict", ""))
    latency_ms = float(body.get("latency_ms", 0.0))

    details: dict[str, Any] = {
        "verdict": verdict,
        "sources": sources,
        "latency_ms": latency_ms,
        "retrieval_mode": body.get("retrieval_mode", ""),
        "tokens_in": (body.get("usage") or {}).get("tokens_in", 0),
        "tokens_out": (body.get("usage") or {}).get("tokens_out", 0),
    }

    checks: dict[str, bool] = {}
    if golden.kind == "answerable":
        checks["expected_files_in_sources"] = _subset(golden.expected_files, sources)
        checks["file_names_in_answer"] = all(name in answer for name in golden.expected_files)
        checks["facts_present"] = _facts_present(golden.must_include, answer)
        checks["disclaimer_present"] = _disclaimer_present(disclaimer, answer)
        checks["no_unsupported_flags"] = not review.get("unsupported_claims")
        checks["latency_ok"] = latency_ms <= LATENCY_BUDGET_MS
    elif golden.kind == "out_of_scope":
        checks["plan_out_of_scope"] = plan.get("in_scope") is False
        checks["no_sources_cited"] = not sources
        checks["disclaimer_present"] = _disclaimer_present(disclaimer, answer)
    else:  # insufficient_evidence
        checks["insufficient_evidence"] = _declined_to_answer(verdict, answer)
        checks["disclaimer_present"] = _disclaimer_present(disclaimer, answer)

    details["missing_facts"] = _missing_facts(golden.must_include, answer)
    details["missing_files"] = [name for name in golden.expected_files if name not in sources]

    return QuestionResult(
        id=golden.id,
        kind=golden.kind,
        passed=all(checks.values()),
        checks=checks,
        details=details,
    )


def _subset(expected: list[str], actual: list[str]) -> bool:
    return all(name in actual for name in expected)


def _facts_present(facts: list[str], answer: str) -> bool:
    lowered = answer.lower()
    return all(fact.lower() in lowered for fact in facts)


def _missing_facts(facts: list[str], answer: str) -> list[str]:
    lowered = answer.lower()
    return [fact for fact in facts if fact.lower() not in lowered]


def _disclaimer_present(disclaimer: str, answer: str) -> bool:
    return bool(disclaimer) and disclaimer in answer


_DECLINE_RE = re.compile(
    r"insufficient evidence|"
    r"(?:do|does) not (?:provide|contain|include|mention|appear|list|specify)|"
    r"not found|"
    r"(?:did|was|were|could) not (?:find|locate)|"
    r"unable to (?:find|locate)|"
    r"returned no result|"
    r"no result|"
    r"no (?:dosing |such )?information|"
    r"not available|"
    r"cannot (?:be )?answer"
)


def _declined_to_answer(verdict: str, answer: str) -> bool:
    """True when the response declines because the corpus cannot answer the question."""
    if verdict == "insufficient_evidence":
        return True
    return bool(_DECLINE_RE.search(answer.lower()))
