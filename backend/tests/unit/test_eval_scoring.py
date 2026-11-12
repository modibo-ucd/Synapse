"""Tests for the deterministic eval scoring functions (no network, no LLM)."""

from __future__ import annotations

from typing import Any

from app.core.constants import MEDICAL_DISCLAIMER
from tests.eval.scoring import GoldenQuestion, _declined_to_answer, score_question


def _body(**overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "answer": (
            "warfarin is contraindicated in pregnancy [S1]\n\n"
            "## Sources\n\n1. dailymed-warfarin.md\n\n"
            f"{MEDICAL_DISCLAIMER}"
        ),
        "sources": ["dailymed-warfarin.md"],
        "disclaimer": MEDICAL_DISCLAIMER,
        "plan": {"complexity": "simple", "in_scope": True, "sub_goals": []},
        "review": {"verdict": "pass", "unsupported_claims": [], "ambiguity_flags": []},
        "retrieval_mode": "hybrid",
        "usage": {"tokens_in": 10, "tokens_out": 5},
        "latency_ms": 1000.0,
    }
    body.update(overrides)
    return body


def _golden(**overrides: Any) -> GoldenQuestion:
    values: dict[str, Any] = {
        "id": "q1",
        "question": "What are the main contraindications for warfarin?",
        "kind": "answerable",
        "expected_files": ["dailymed-warfarin.md"],
        "must_include": ["pregnancy"],
    }
    values.update(overrides)
    return GoldenQuestion.model_validate(values)


def test_answerable_passes_when_all_checks_hold() -> None:
    result = score_question(_golden(), _body())
    assert result.passed is True
    assert result.checks["expected_files_in_sources"] is True
    assert result.checks["file_names_in_answer"] is True
    assert result.checks["facts_present"] is True
    assert result.checks["disclaimer_present"] is True
    assert result.checks["no_unsupported_flags"] is True


def test_answerable_fails_on_missing_fact() -> None:
    golden = _golden(must_include=["pregnancy", "malignant hypertension"])
    result = score_question(golden, _body())
    assert result.checks["facts_present"] is False
    assert result.details["missing_facts"] == ["malignant hypertension"]
    assert result.passed is False


def test_answerable_fails_on_missing_file() -> None:
    golden = _golden(expected_files=["dailymed-warfarin.md", "dailymed-apixaban.md"])
    result = score_question(golden, _body())
    assert result.checks["expected_files_in_sources"] is False
    assert result.checks["file_names_in_answer"] is False
    assert result.details["missing_files"] == ["dailymed-apixaban.md"]
    assert result.passed is False


def test_answerable_fails_on_unsupported_flags() -> None:
    result = score_question(
        _golden(),
        _body(review={"verdict": "revise", "unsupported_claims": ["x"], "ambiguity_flags": []}),
    )
    assert result.checks["no_unsupported_flags"] is False
    assert result.passed is False


def test_out_of_scope_passes_with_no_sources() -> None:
    golden = _golden(kind="out_of_scope", expected_files=[], must_include=[])
    body = _body(
        sources=[],
        answer=f"outside the scope\n\n## Sources\n\nNone.\n\n{MEDICAL_DISCLAIMER}",
        plan={"complexity": "simple", "in_scope": False, "sub_goals": []},
    )
    result = score_question(golden, body)
    assert result.checks["plan_out_of_scope"] is True
    assert result.checks["no_sources_cited"] is True
    assert result.passed is True


def test_out_of_scope_fails_when_in_scope() -> None:
    golden = _golden(kind="out_of_scope", expected_files=[], must_include=[])
    result = score_question(golden, _body())
    assert result.checks["plan_out_of_scope"] is False
    assert result.passed is False


def test_insufficient_evidence_passes() -> None:
    golden = _golden(kind="insufficient_evidence", expected_files=[], must_include=[])
    body = _body(
        sources=[],
        answer=(
            "Insufficient evidence in the corpus to answer this question.\n\n"
            f"{MEDICAL_DISCLAIMER}"
        ),
        review={
            "verdict": "insufficient_evidence",
            "unsupported_claims": [],
            "ambiguity_flags": [],
        },
    )
    result = score_question(golden, body)
    assert result.checks["insufficient_evidence"] is True
    assert result.checks["disclaimer_present"] is True
    assert result.passed is True


def test_insufficient_evidence_accepts_decline_phrase() -> None:
    golden = _golden(kind="insufficient_evidence", expected_files=[], must_include=[])
    body = _body(
        sources=["dailymed-warfarin.md"],
        answer=(
            "The retrieved evidence does not provide recommended dosing information "
            "for losartan.\n\n"
            f"{MEDICAL_DISCLAIMER}"
        ),
        review={"verdict": "pass", "unsupported_claims": [], "ambiguity_flags": []},
    )
    result = score_question(golden, body)
    assert result.checks["insufficient_evidence"] is True
    assert result.passed is True


def test_decline_detection_variants() -> None:
    assert _declined_to_answer(
        "pass", "The provided passages do not include a dosing recommendation"
    )
    assert _declined_to_answer("pass", "A lookup for the drug returned no result")
    assert _declined_to_answer("pass", "The evidence does not provide dosing information")
    assert _declined_to_answer("pass", "Insufficient evidence in the corpus to answer")
    assert _declined_to_answer("insufficient_evidence", "anything")
    assert not _declined_to_answer("pass", "metformin is contraindicated below 30")
