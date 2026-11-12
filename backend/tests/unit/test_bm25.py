"""Tests for the BM25 index and tokenizer."""

from __future__ import annotations

from app.retrieval.bm25 import BM25Index, tokenize


def test_tokenizer_keeps_numbers_units_and_abbreviations() -> None:
    assert tokenize("INR 30 mL/min") == ["inr", "30", "ml/min"]
    assert tokenize("dose 1.73 m 2") == ["dose", "1.73", "m", "2"]
    assert tokenize("Warfarin sodium tablets") == ["warfarin", "sodium", "tablets"]


def test_tokenizer_lowercases() -> None:
    assert tokenize("Warfarin INR") == ["warfarin", "inr"]


def test_bm25_ranks_matching_document_higher() -> None:
    index = BM25Index(
        [
            "warfarin causes bleeding and requires INR monitoring",
            "acetaminophen relieves fever and minor pain",
            "warfarin bleeding risk with warfarin warfarin",
        ]
    )
    ranked = index.search("warfarin bleeding", k=3)
    assert ranked[0][0] == 2


def test_bm25_ignores_documents_without_query_terms() -> None:
    index = BM25Index(["the quick brown fox", "a completely different topic"])
    ranked = index.search("quick fox", k=3)
    assert [doc_index for doc_index, _ in ranked] == [0]


def test_bm25_empty_corpus() -> None:
    index = BM25Index([])
    assert index.search("anything") == []
