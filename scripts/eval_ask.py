"""Run the public + extra questions through the real /ask pipeline.

Development helper (Task 7). Prints each answer's verdict, retrieval mode,
latency, token usage and a truncated answer so retrieval/answer quality can be
reviewed by eye. Never prints secrets.

Usage:
    python scripts/eval_ask.py
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app

QUESTIONS = [
    "What are the main contraindications for warfarin?",
    (
        "Compare the contraindications of warfarin and apixaban. What conditions "
        "are shared and which are unique to each drug?"
    ),
    (
        "A patient currently on warfarin is prescribed sertraline. What is the risk "
        "of bleeding and what monitoring is recommended?"
    ),
    (
        "A patient with an eGFR of 25 mL/min is being considered for metformin. Is "
        "metformin contraindicated at this level of renal function, and what is the "
        "threshold?"
    ),
    "What is the mechanism of action of apixaban?",
    "What does INR stand for and why is it monitored?",
]


def main() -> None:
    app = create_app(get_settings())
    with TestClient(app) as client:
        for question in QUESTIONS:
            resp = client.post("/ask", json={"question": question})
            print(f"=== {question}")
            if resp.status_code != 200:
                print(f"status={resp.status_code} body={resp.text[:300]}\n")
                continue
            body = resp.json()
            print(
                f"status=200 mode={body['retrieval_mode']} verdict={body['review']['verdict']} "
                f"latency_ms={body['latency_ms']:.0f} tokens={body['usage']}"
            )
            print(f"sources={body['sources']}")
            print(body["answer"][:900])
            print()


if __name__ == "__main__":
    main()
