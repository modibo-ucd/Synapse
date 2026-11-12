"""Tests for structure-aware chunking."""

from __future__ import annotations

from app.retrieval.chunker import chunk_document, count_tokens
from app.schemas.domain import CorpusDocument, SourceType


def _doc(
    raw_text: str,
    *,
    source_file: str = "dailymed-test.md",
    drug_name: str = "test",
    source_type: SourceType = "dailymed",
) -> CorpusDocument:
    return CorpusDocument(
        source_file=source_file,
        drug_name=drug_name,
        source_type=source_type,
        title=f"{drug_name} ({source_type})",
        raw_text=raw_text,
    )


def test_count_tokens_approximation() -> None:
    assert count_tokens("", 4.0) == 1
    assert count_tokens("abcd", 4.0) == 1
    assert count_tokens("abcde", 4.0) == 2
    assert count_tokens("x" * 40, 10.0) == 4


def test_heading_path_preserved() -> None:
    doc = _doc(
        "# Test (DailyMed label)\n\n"
        "Source: https://example\n\n"
        "## 4 CONTRAINDICATIONS\n\n"
        "Do not use in X.\n\n"
        "### 4.1 Sub\n\n"
        "More detail.\n"
    )
    chunks = chunk_document(doc)
    paths = {c.section_path for c in chunks}
    assert "test > 4 CONTRAINDICATIONS" in paths
    assert "test > 4 CONTRAINDICATIONS > 4.1 Sub" in paths
    sub = next(c for c in chunks if c.section == "4.1 Sub")
    assert sub.text == "More detail."


def test_table_kept_whole_when_section_split() -> None:
    paragraphs = [f"Paragraph {i}. " + "word " * 20 for i in range(30)]
    content = "\n\n".join(
        paragraphs[:10]
        + ["| Event | Rate |\n| Headache | 5% |\n| Nausea | 3% |"]
        + paragraphs[10:]
    )
    doc = _doc("# Test (DailyMed label)\n\n## 6 ADVERSE REACTIONS\n\n" + content)
    chunks = chunk_document(doc, max_tokens=60, overlap_tokens=0)
    table_chunks = [c for c in chunks if "Headache" in c.text]
    assert len(table_chunks) == 1
    assert "Nausea" in table_chunks[0].text


def test_size_limit_respected() -> None:
    paragraphs = [f"P{i} " + "x" * 80 for i in range(20)]
    doc = _doc("# Test (DailyMed label)\n\n## 6 ADVERSE REACTIONS\n\n" + "\n\n".join(paragraphs))
    chunks = chunk_document(doc, max_tokens=100, overlap_tokens=0)
    assert len(chunks) > 1
    assert all(c.token_count <= 100 for c in chunks)


def test_deterministic_chunk_ids() -> None:
    doc = _doc("# Test (DailyMed label)\n\n## 6 ADVERSE REACTIONS\n\nA.\n\nB.\n\nC.\n")
    first = chunk_document(doc, max_tokens=1, overlap_tokens=0)
    second = chunk_document(doc, max_tokens=1, overlap_tokens=0)
    ids_first = [c.chunk_id for c in first]
    ids_second = [c.chunk_id for c in second]
    assert len(first) == 3
    assert ids_first == ids_second
    assert len(set(ids_first)) == len(ids_first)


def test_contraindications_never_split() -> None:
    paragraphs = [f"Item {i}." for i in range(50)]
    doc = _doc("# Test (DailyMed label)\n\n## 4 CONTRAINDICATIONS\n\n" + "\n\n".join(paragraphs))
    chunks = chunk_document(doc, max_tokens=10)
    assert len(chunks) == 1
    assert "Item 0." in chunks[0].text and "Item 49." in chunks[0].text


def test_dosage_section_never_split() -> None:
    paragraphs = [f"Step {i}." for i in range(50)]
    doc = _doc(
        "# Test (DailyMed label)\n\n## 2 DOSAGE AND ADMINISTRATION\n\n### 2.1 Dosing\n\n"
        + "\n\n".join(paragraphs)
    )
    chunks = chunk_document(doc, max_tokens=10)
    dosing = [c for c in chunks if "Step" in c.text]
    assert len(dosing) == 1
    assert "Step 49." in dosing[0].text


def test_boxed_warning_never_split() -> None:
    paragraphs = [f"Warning item {i}." for i in range(50)]
    doc = _doc("# Test (DailyMed label)\n\n## WARNING: BLEEDING RISK\n\n" + "\n\n".join(paragraphs))
    chunks = chunk_document(doc, max_tokens=10)
    assert len(chunks) == 1


def test_overlap_between_chunks() -> None:
    paragraphs = [f"Paragraph number {i} with some words here." for i in range(30)]
    doc = _doc("# Test (DailyMed label)\n\n## 6 ADVERSE REACTIONS\n\n" + "\n\n".join(paragraphs))
    chunks = chunk_document(doc, max_tokens=40, overlap_tokens=25)
    assert len(chunks) > 1
    for prev, nxt in zip(chunks, chunks[1:], strict=False):
        prev_paras = [p for p in prev.text.split("\n\n") if p.strip()]
        nxt_paras = [p for p in nxt.text.split("\n\n") if p.strip()]
        assert prev_paras and nxt_paras
        assert prev_paras[-1] in nxt_paras


def test_oversized_table_repeats_header() -> None:
    rows = [f"Row {i} | value {i} | more {i}" for i in range(30)]
    table = "| Column A | Column B | Column C |\n" + "\n".join(rows)
    doc = _doc("# Test (DailyMed label)\n\n## 6 ADVERSE REACTIONS\n\n" + table)
    chunks = chunk_document(doc, max_tokens=30)
    table_chunks = [c for c in chunks if "Column A" in c.text]
    assert len(table_chunks) > 1
    for chunk in table_chunks:
        assert chunk.text.splitlines()[0].startswith("| Column A")


def test_embedding_text_prefixed() -> None:
    doc = _doc(
        "# Warfarin (DailyMed label)\n\n## 4 CONTRAINDICATIONS\n\nBleeding.\n",
        drug_name="warfarin",
    )
    chunk = chunk_document(doc)[0]
    assert chunk.embedding_text.startswith("warfarin (dailymed) warfarin > 4 CONTRAINDICATIONS\n")
    assert "Bleeding." in chunk.embedding_text


def test_no_headings_single_chunk() -> None:
    doc = _doc("Just some plain text without any headings.\n\nMore text.\n")
    chunks = chunk_document(doc)
    assert len(chunks) == 1
    assert chunks[0].section == ""
    assert chunks[0].section_path == "test"


def test_empty_document_no_chunks() -> None:
    assert chunk_document(_doc("")) == []


def test_heading_without_content_skipped() -> None:
    doc = _doc("# Test (DailyMed label)\n\n## 4 CONTRAINDICATIONS\n\n## 5 WARNINGS\n\nSome text.\n")
    chunks = chunk_document(doc)
    sections = {c.section for c in chunks}
    assert "4 CONTRAINDICATIONS" not in sections
    assert "5 WARNINGS" in sections
