"""Tests for corpus loading."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.errors import ConfigurationError
from app.retrieval.loader import load_documents, load_glossary, load_source_texts


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def test_derives_drug_and_source_from_filename(tmp_path: Path) -> None:
    _write(
        tmp_path / "dailymed-warfarin.md",
        "# Warfarin (DailyMed label)\n\n## 4 CONTRAINDICATIONS\n\n- Bleeding\n",
    )
    _write(
        tmp_path / "medlineplus-warfarin.md",
        "# Warfarin (MedlinePlus)\n\n## IMPORTANT WARNING:\n\nBleeding.\n",
    )
    documents = load_documents(tmp_path)
    assert len(documents) == 2
    by_file = {d.source_file: d for d in documents}
    assert by_file["dailymed-warfarin.md"].drug_name == "warfarin"
    assert by_file["dailymed-warfarin.md"].source_type == "dailymed"
    assert by_file["medlineplus-warfarin.md"].source_type == "medlineplus"


def test_glossary_file_is_not_a_document(tmp_path: Path) -> None:
    _write(tmp_path / "GLOSSARY.md", "## Core concepts\n- **Term**: def.\n")
    _write(tmp_path / "dailymed-x.md", "# X (DailyMed label)\n")
    documents = load_documents(tmp_path)
    assert [d.source_file for d in documents] == ["dailymed-x.md"]
    glossary = load_glossary(tmp_path)
    assert [g.term for g in glossary] == ["Term"]


def test_empty_file_loads_with_empty_text(tmp_path: Path) -> None:
    _write(tmp_path / "dailymed-empty.md", "")
    documents = load_documents(tmp_path)
    assert documents[0].raw_text == ""


def test_unknown_filename_prefix_raises(tmp_path: Path) -> None:
    _write(tmp_path / "other-drug.md", "# Other\n")
    with pytest.raises(ConfigurationError):
        load_documents(tmp_path)


def test_missing_glossary_is_graceful(tmp_path: Path) -> None:
    assert load_glossary(tmp_path) == []


def test_missing_directory_is_empty(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist"
    assert load_documents(missing) == []
    assert load_glossary(missing) == []


def test_load_source_texts_includes_glossary_and_normalizes_crlf(tmp_path: Path) -> None:
    (tmp_path / "dailymed-warfarin.md").write_bytes(
        b"# Warfarin (DailyMed label)\r\n\r\n## 4 CONTRAINDICATIONS\r\n\r\nBleeding.\r\n"
    )
    (tmp_path / "GLOSSARY.md").write_bytes(b"# Pharmacology Glossary\r\n\r\n- **INR**: ratio.\r\n")
    texts = load_source_texts(tmp_path)
    assert set(texts) == {"dailymed-warfarin.md", "GLOSSARY.md"}
    assert "\r" not in texts["dailymed-warfarin.md"]
    assert "\r" not in texts["GLOSSARY.md"]
