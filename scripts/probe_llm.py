"""Probe the OpenAI-compatible LiteLLM proxy and report its capabilities.

Development/recon helper (Task 0). It NEVER prints the API key or the full base
URL. It reports which of the documented environment variable NAMES are present
(never their values), and exercises: (a) chat completion, (b) structured output,
(c) native function calling, (d) embeddings (single + batch of 100), and
(e) model listing.

Usage:
    python scripts/probe_llm.py
"""

from __future__ import annotations

import json
import os
import sys
import time

from dotenv import load_dotenv

REQUIRED_NAMES = (
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
    "OPENAI_MODEL",
    "OPENAI_EMBEDDING_MODEL",
)
# Known typo observed in a local .env: OPENAI_BASE_UR instead of OPENAI_BASE_URL.
# Tolerated as a fallback so the probe can still run; reported explicitly.
BASE_URL_ALIASES = ("OPENAI_BASE_URL", "OPENAI_BASE_UR")


def section(title: str) -> None:
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


def run_probe(name: str, fn) -> None:
    start = time.perf_counter()
    try:
        result = fn()
        elapsed_ms = (time.perf_counter() - start) * 1000
        print(f"[OK] {name} ({elapsed_ms:.0f} ms)")
        if result:
            print(result)
    except Exception as exc:  # keep probing even if one capability fails
        elapsed_ms = (time.perf_counter() - start) * 1000
        print(f"[FAIL] {name} ({elapsed_ms:.0f} ms): {type(exc).__name__}: {exc}")


def main() -> int:
    load_dotenv(override=False)

    section("Environment (variable NAMES only)")
    for name in REQUIRED_NAMES:
        value = os.environ.get(name, "").strip()
        print(f"  {name:<28} {'present' if value else 'MISSING'}")
    for alias in BASE_URL_ALIASES:
        if alias != "OPENAI_BASE_URL" and os.environ.get(alias, "").strip():
            print(f"  {alias:<28} present (likely typo for OPENAI_BASE_URL)")

    key = os.environ.get("OPENAI_API_KEY", "").strip()
    base_url = ""
    for name in BASE_URL_ALIASES:
        if os.environ.get(name, "").strip():
            base_url = os.environ.get(name).strip()
            break
    model = os.environ.get("OPENAI_MODEL", "").strip()
    embedding_model = os.environ.get(
        "OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"
    ).strip()

    print(f"  base_url               : {'present' if base_url else 'MISSING'}")
    print(f"  chat model            : {model or 'MISSING'}")
    print(f"  embedding model       : {embedding_model}")

    if not key or not base_url:
        print("\nSkipping network probes: OPENAI_API_KEY and/or a base URL are missing.")
        return 2

    try:
        from openai import OpenAI
    except ImportError:
        print("\nThe 'openai' package is not installed. Run: python -m pip install openai")
        return 2

    client = OpenAI(api_key=key, base_url=base_url, timeout=60.0, max_retries=0)

    def chat():
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Reply with the single word: pong"}],
            temperature=0,
        )
        content = (resp.choices[0].message.content or "").strip()
        usage = getattr(resp, "usage", None)
        tok = ""
        if usage is not None:
            tok = f" (in={usage.prompt_tokens}, out={usage.completion_tokens})"
        return f"  reply={content[:60]!r}{tok}"

    run_probe(f"(a) chat completion [{model}]", chat)

    def structured():
        schema = {
            "type": "object",
            "properties": {
                "complexity": {"type": "string", "enum": ["simple", "multi_hop"]},
                "in_scope": {"type": "boolean"},
                "sub_goals": {"type": "array", "items": {"type": "string"}, "maxItems": 3},
            },
            "required": ["complexity", "in_scope", "sub_goals"],
            "additionalProperties": False,
        }
        last_err: Exception | None = None
        for fmt in (
            {
                "type": "json_schema",
                "json_schema": {"name": "plan", "schema": schema, "strict": True},
            },
            {"type": "json_object"},
        ):
            try:
                resp = client.chat.completions.create(
                    model=model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You output only JSON matching the requested schema.",
                        },
                        {
                            "role": "user",
                            "content": "Classify: 'warfarin vs apixaban contraindications'",
                        },
                    ],
                    response_format=fmt,  # type: ignore[arg-type]
                    temperature=0,
                )
                raw = resp.choices[0].message.content or ""
                parsed = json.loads(raw)
                mode = "json_schema" if fmt.get("type") == "json_schema" else "json_object"
                return f"  mode={mode} parsed={parsed!r}"
            except Exception as exc:  # noqa: BLE001 - intentional capability fallback
                last_err = exc
        raise last_err  # type: ignore[misc]

    run_probe("(b) structured output", structured)

    def tools():
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "What is the weather in Paris?"}],
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "description": "Get the current weather for a city.",
                        "parameters": {
                            "type": "object",
                            "properties": {"city": {"type": "string"}},
                            "required": ["city"],
                        },
                    },
                }
            ],
            tool_choice="auto",
            temperature=0,
        )
        calls = resp.choices[0].message.tool_calls or []
        if not calls:
            return "  no tool_calls returned"
        return "\n".join(
            f"  tool={c.function.name} args={c.function.arguments}" for c in calls
        )

    run_probe("(c) native function calling", tools)

    def embeddings():
        single = client.embeddings.create(
            model=embedding_model, input="warfarin bleeding risk"
        )
        dim = len(single.data[0].embedding)
        batch = client.embeddings.create(
            model=embedding_model,
            input=[f"sample passage number {i}" for i in range(100)],
        )
        return f"  dimension={dim}  batch_count={len(batch.data)} (requested 100)"

    run_probe(f"(d) embeddings [{embedding_model}]", embeddings)

    def models():
        try:
            listing = client.models.list()
            ids = sorted({m.id for m in listing.data})
            shown = ", ".join(ids[:50])
            if len(ids) > 50:
                shown += f", ... ({len(ids)} total)"
            return f"  models: {shown}"
        except Exception as exc:  # noqa: BLE001
            return f"  models.list() NOT allowed: {type(exc).__name__}: {exc}"

    run_probe("(e) models.list()", models)

    print("\nDone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
