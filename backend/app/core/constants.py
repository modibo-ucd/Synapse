"""Shared constants used across the application."""

from __future__ import annotations

# Appended verbatim to every generated answer by code (never by the LLM).
MEDICAL_DISCLAIMER = (
    "This information is for research and educational purposes only and is not "
    "medical advice. It is generated from drug labeling and consumer medication "
    "documents and must not be used to diagnose, treat, or make prescribing "
    "decisions. Always consult a qualified healthcare professional."
)

# Pipeline budgets (defaults; overridable via Settings/environment).
MAX_SUB_GOALS = 5
MAX_TOOL_CALLS = 4
REQUEST_TIMEOUT_S = 90.0

# API contract limits.
MAX_QUESTION_LEN = 2000

# Structure-aware chunking defaults (configurable via Settings/environment).
CHUNK_MAX_TOKENS = 800
CHUNK_OVERLAP_TOKENS = 60
CHARS_PER_TOKEN = 4.0

# Hybrid retrieval defaults (configurable via Settings/environment).
RRF_K = 60
RETRIEVAL_TOP_K = 20
RETRIEVAL_TOKEN_BUDGET = 4000
INDEX_READY_TIMEOUT_S = 30.0

# Agent tool execution budget.
TOOL_TIMEOUT_S = 5.0
