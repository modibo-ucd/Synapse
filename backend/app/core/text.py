"""Small, dependency-free text-normalization helpers.

These run at the API boundary so that control characters and inconsistent
whitespace never reach the LLM, the retrieval index, or the logging layer.
"""

from __future__ import annotations

import re

# Control characters (C0 except \t\n\r, plus DEL) are removed. \t and \n are
# legitimate whitespace and are collapsed by ``sanitize_question`` instead.
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def strip_control_characters(text: str) -> str:
    """Remove C0 control characters and DEL, preserving other whitespace."""
    return _CONTROL_RE.sub("", text)


def sanitize_question(text: str) -> str:
    """Strip control characters and collapse all whitespace runs to single spaces."""
    return " ".join(strip_control_characters(text).split())
