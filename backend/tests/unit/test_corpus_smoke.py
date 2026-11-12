"""Smoke tests against the committed corpus (no network, deterministic)."""

from __future__ import annotations

from pathlib import Path

from app.retrieval.chunker import chunk_document
from app.retrieval.loader import load_documents, load_glossary

CORPUS_DIR = Path(__file__).resolve().parents[3] / "corpus"


def test_real_corpus_has_twenty_drug_documents() -> None:
    documents = load_documents(CORPUS_DIR)
    assert len(documents) == 20
    drugs = {d.drug_name for d in documents}
    assert {"warfarin", "apixaban", "metformin", "sertraline"} <= drugs
    assert all(d.source_type in {"dailymed", "medlineplus"} for d in documents)


def test_real_glossary_parses_key_terms() -> None:
    glossary = load_glossary(CORPUS_DIR)
    terms = {entry.term: entry for entry in glossary}
    assert terms["INR"].aliases == ["International Normalized Ratio"]
    assert "direct oral anticoagulant" in terms["DOAC"].definition
    assert len(glossary) >= 25


def test_warfarin_contraindications_is_single_chunk() -> None:
    warfarin = next(
        d for d in load_documents(CORPUS_DIR) if d.source_file == "dailymed-warfarin.md"
    )
    contraindications = [c for c in chunk_document(warfarin) if c.section == "4 CONTRAINDICATIONS"]
    assert len(contraindications) == 1
    assert "Hemorrhagic tendencies or blood dyscrasias" in contraindications[0].text


def test_apixaban_table_kept_whole() -> None:
    apixaban = next(
        d for d in load_documents(CORPUS_DIR) if d.source_file == "dailymed-apixaban.md"
    )
    table_chunks = [c for c in chunk_document(apixaban) if "ELIQUIS N=9088" in c.text]
    assert len(table_chunks) == 1
    text = table_chunks[0].text
    for row in ("327 (2.13)", "141 (0.93)", "10 (0.06)"):
        assert row in text


def test_metformin_egfr_threshold_retrievable() -> None:
    metformin = next(
        d for d in load_documents(CORPUS_DIR) if d.source_file == "dailymed-metformin.md"
    )
    chunks = chunk_document(metformin)
    assert any("eGFR below 30" in c.text for c in chunks)
    assert any("eGFR between 30 to 45" in c.text for c in chunks)
