"""Tests for chunk character spans into the normalized source text."""

from __future__ import annotations

from pathlib import Path

from app.retrieval.chunker import chunk_document
from app.retrieval.loader import load_documents
from app.schemas.domain import CorpusDocument


def _doc(raw_text: str, *, drug_name: str = "test") -> CorpusDocument:
    return CorpusDocument(
        source_file="dailymed-test.md",
        drug_name=drug_name,
        source_type="dailymed",
        title=f"{drug_name} (dailymed)",
        raw_text=raw_text,
    )


def test_spans_in_bounds_ordered_and_nonempty() -> None:
    doc = _doc(
        "# Test (DailyMed label)\n\n"
        "## 6 ADVERSE REACTIONS\n\n"
        + "\n\n".join(f"P{i} " + "x" * 80 for i in range(20))
        + "\n"
    )
    chunks = chunk_document(doc, max_tokens=60, overlap_tokens=0)
    assert len(chunks) > 1
    starts = [chunk.start_char for chunk in chunks]
    assert starts == sorted(starts)
    for chunk in chunks:
        assert 0 <= chunk.start_char < chunk.end_char <= len(doc.raw_text)
        assert doc.raw_text[chunk.start_char:chunk.end_char].strip()


def test_span_starts_at_block_boundary() -> None:
    doc = _doc(
        "# Test (DailyMed label)\n\n## 4 CONTRAINDICATIONS\n\nItem 0.\n\nItem 1.\n"
    )
    chunk = chunk_document(doc, max_tokens=5)[0]
    sliced = doc.raw_text[chunk.start_char:chunk.end_char]
    assert sliced.startswith("Item 0.")
    assert "Item 1." in sliced


def test_non_bmp_character_inside_span() -> None:
    doc = _doc(
        "# Test (DailyMed label)\n\n## 6 ADVERSE REACTIONS\n\nReaction 😀 occurs.\n"
    )
    chunk = chunk_document(doc)[0]
    assert "😀" in doc.raw_text[chunk.start_char:chunk.end_char]


def test_spans_survive_crlf_input(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "dailymed-warfarin.md").write_bytes(
        b"# Warfarin (DailyMed label)\r\n\r\n## 4 CONTRAINDICATIONS\r\n\r\nBleeding.\r\n"
    )
    document = load_documents(corpus)[0]
    assert "\r" not in document.raw_text  # the loader normalized line endings
    chunk = chunk_document(document)[0]
    assert document.raw_text[chunk.start_char:chunk.end_char].startswith("Bleeding.")
