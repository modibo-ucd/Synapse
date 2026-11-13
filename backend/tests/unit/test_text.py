"""Tests for the text-normalization helpers used at the API boundary."""

from __future__ import annotations

from app.core.text import sanitize_question, strip_control_characters, utf16_offset


def test_strip_control_characters_removes_c0_and_del_but_keeps_whitespace() -> None:
    assert strip_control_characters("a\x00b\x1fc\x7fd") == "abcd"
    assert strip_control_characters("tab\tand\nnewline") == "tab\tand\nnewline"


def test_sanitize_question_collapses_whitespace() -> None:
    assert sanitize_question("  warfarin\tcontraindications\n ") == "warfarin contraindications"
    assert sanitize_question("hello\x00world") == "helloworld"


def test_sanitize_question_empty_for_control_characters_only() -> None:
    assert sanitize_question("\x00\x01\x02\x7f") == ""


def test_sanitize_question_preserves_unicode() -> None:
    assert sanitize_question("  métabolite — ドラッグ ✓  ") == "métabolite — ドラッグ ✓"


def test_utf16_offset_counts_code_units() -> None:
    assert utf16_offset("abc", 0) == 0
    assert utf16_offset("abc", 3) == 3
    # A non-BMP character (emoji) occupies two UTF-16 code units.
    assert utf16_offset("a😀b", 1) == 1
    assert utf16_offset("a😀b", 2) == 3
    assert utf16_offset("a😀b", 3) == 4
