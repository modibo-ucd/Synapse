"""Eval harness CLI: hit the running API and score the golden questions.

This is a live-LLM tool (marker ``llm_live``) and is never run by the default
pytest suite. It POSTs each golden question to a running Synapse server, scores
the response deterministically, prints a results table, and writes it to
``docs/eval_results.md``.

Usage:
    python -m tests.eval.run [--only ID] [--base-url http://localhost:8000] [--runs 2]
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import yaml

from tests.eval.scoring import GoldenQuestion, GoldenSet, QuestionResult, score_question

REPO_ROOT = Path(__file__).resolve().parents[3]
GOLDEN_PATH = Path(__file__).with_name("golden_questions.yaml")
RESULTS_PATH = REPO_ROOT / "docs" / "eval_results.md"
DEFAULT_BASE_URL = "http://localhost:8000"


def load_golden(path: Path) -> GoldenSet:
    """Load and validate the golden question set from YAML."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return GoldenSet.model_validate(raw)


async def _ask(client: httpx.AsyncClient, question: str) -> dict[str, Any]:
    resp = await client.post("/ask", json={"question": question})
    if resp.status_code != 200:
        return {"error": f"HTTP {resp.status_code}", "body": resp.text[:300]}
    return dict(resp.json())


async def _collect(
    base_url: str, questions: list[GoldenQuestion], runs: int
) -> list[tuple[GoldenQuestion, QuestionResult]]:
    """Run each question ``runs`` times against the API and score every response."""
    timeout = httpx.Timeout(150.0, connect=10.0)
    async with httpx.AsyncClient(base_url=base_url, timeout=timeout) as client:
        rows: list[tuple[GoldenQuestion, QuestionResult]] = []
        for question in questions:
            for run_index in range(1, runs + 1):
                body = await _ask(client, question.question)
                if "error" in body:
                    result = QuestionResult(
                        id=_label(question.id, runs, run_index),
                        kind=question.kind,
                        passed=False,
                        checks={"request_ok": False},
                        details=body,
                    )
                else:
                    result = score_question(question, body)
                    result.id = _label(question.id, runs, run_index)
                rows.append((question, result))
        return rows


def _label(question_id: str, runs: int, run_index: int) -> str:
    return f"{question_id}/r{run_index}" if runs > 1 else question_id


def _latency_summary(rows: list[tuple[GoldenQuestion, QuestionResult]]) -> str:
    """Return a ``p50/p95 (n)`` summary over the successful responses' latency."""
    latencies = sorted(
        float(result.details["latency_ms"])
        for _, result in rows
        if "error" not in result.details and result.details.get("latency_ms") is not None
    )
    if not latencies:
        return "latency p50/p95: n/a"

    def percentile(p: float) -> float:
        index = (len(latencies) - 1) * p
        lower = int(index)
        upper = min(lower + 1, len(latencies) - 1)
        weight = index - lower
        return latencies[lower] * (1 - weight) + latencies[upper] * weight

    return (
        f"latency p50={percentile(0.50):.0f} ms, "
        f"p95={percentile(0.95):.0f} ms (n={len(latencies)})"
    )


def render_markdown(
    rows: list[tuple[GoldenQuestion, QuestionResult]], base_url: str, generated: str
) -> str:
    """Render the results table plus per-question details as Markdown."""
    passed = sum(1 for _, result in rows if result.passed)
    lines = [
        "# Eval results",
        "",
        f"- Base URL: {base_url}",
        f"- Generated: {generated}",
        f"- Passed: {passed}/{len(rows)}",
        f"- {_latency_summary(rows)}",
        "",
        "| id | kind | result | verdict | latency_ms | retrieval |",
        "|----|------|--------|---------|------------|-----------|",
    ]
    for _, result in rows:
        lines.append(
            f"| {result.id} | {result.kind} | {'PASS' if result.passed else 'FAIL'} "
            f"| {result.details.get('verdict', '-')} "
            f"| {result.details.get('latency_ms', '-')} "
            f"| {result.details.get('retrieval_mode', '-')} |"
        )
    lines.extend(["", "## Details", ""])
    for question, result in rows:
        lines.append(f"### {result.id} — {question.question}")
        lines.append("")
        if question.expected_files:
            lines.append(f"- Expected files: {', '.join(question.expected_files)}")
        if question.must_include:
            lines.append(f"- Must include: {', '.join(question.must_include)}")
        for check, ok in result.checks.items():
            lines.append(f"- {'PASS' if ok else 'FAIL'} {check}")
        for key in ("missing_facts", "missing_files"):
            missing = result.details.get(key) or []
            if missing:
                lines.append(f"- Missing ({key}): {', '.join(missing)}")
        if "error" in result.details:
            lines.append(f"- Error: {result.details['error']}")
        lines.append("")
    return "\n".join(lines)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the eval harness against a running API.")
    parser.add_argument(
        "--only", help="run only the question(s) with these ids (comma-separated)"
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="running API base URL")
    parser.add_argument("--runs", type=int, default=1, help="repeat each question N times")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    golden = load_golden(GOLDEN_PATH)
    only_ids = {i.strip() for i in args.only.split(",")} if args.only else None
    questions = [q for q in golden.questions if only_ids is None or q.id in only_ids]
    if not questions:
        print(f"No question matched ids {args.only!r}.", file=sys.stderr)
        return 2

    rows = asyncio.run(_collect(args.base_url, questions, args.runs))
    generated = datetime.now(UTC).isoformat(timespec="seconds")
    markdown = render_markdown(rows, args.base_url, generated)
    RESULTS_PATH.write_text(markdown, encoding="utf-8")
    print(markdown)
    passed = sum(1 for _, result in rows if result.passed)
    print(f"{passed}/{len(rows)} passed")
    print(_latency_summary(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
