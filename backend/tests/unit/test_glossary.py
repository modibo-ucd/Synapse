"""Tests for GLOSSARY.md parsing."""

from __future__ import annotations

from app.retrieval.glossary import parse_glossary


def test_parse_basic_entry() -> None:
    text = "## Core concepts\n- **Indication**: an official reason a drug is approved for use.\n"
    entries = parse_glossary(text)
    assert len(entries) == 1
    entry = entries[0]
    assert entry.term == "Indication"
    assert entry.aliases == []
    assert entry.definition == "an official reason a drug is approved for use."
    assert entry.category == "Core concepts"


def test_parse_alias_in_parentheses() -> None:
    text = (
        "## Pharmacokinetics\n"
        "- **Half-life (t½)**: the time for the drug's plasma concentration to fall by half.\n"
    )
    entries = parse_glossary(text)
    assert entries[0].term == "Half-life"
    assert entries[0].aliases == ["t½"]


def test_parse_comma_separated_aliases_with_eg() -> None:
    text = "## Pharmacokinetics\n- **CYP enzymes (e.g. CYP3A4, CYP2D6)**: liver enzymes.\n"
    entries = parse_glossary(text)
    assert entries[0].term == "CYP enzymes"
    assert entries[0].aliases == ["CYP3A4", "CYP2D6"]


def test_parse_quoted_alias() -> None:
    text = '## Safety\n- **Boxed warning (previously "black box")**: the strongest FDA warning.\n'
    entries = parse_glossary(text)
    assert entries[0].term == "Boxed warning"
    assert entries[0].aliases == ["black box"]


def test_quoted_term_is_not_an_alias() -> None:
    text = (
        '## Reading drug labels\n'
        '- **"Highlights of Prescribing Information"**: the one-page summary.\n'
    )
    entries = parse_glossary(text)
    assert entries[0].term == '"Highlights of Prescribing Information"'
    assert entries[0].aliases == []


def test_parse_multiline_definition() -> None:
    text = (
        "## Pharmacokinetics\n"
        "- **CYP enzymes (e.g. CYP3A4, CYP2D6)**: liver enzymes that metabolize most drugs."
        " Inhibitors raise\n"
        "  drug levels, inducers lower them.\n"
    )
    entries = parse_glossary(text)
    assert entries[0].definition == (
        "liver enzymes that metabolize most drugs. Inhibitors raise drug levels,"
        " inducers lower them."
    )


def test_parse_multiple_entries_and_categories() -> None:
    text = (
        "## Core concepts\n"
        "- **Indication**: official reason.\n"
        "- **Contraindication**: unsafe condition.\n"
        "## Safety\n"
        "- **INR (International Normalized Ratio)**: a blood test.\n"
    )
    entries = parse_glossary(text)
    assert [e.term for e in entries] == ["Indication", "Contraindication", "INR"]
    assert entries[2].category == "Safety"
    assert entries[2].aliases == ["International Normalized Ratio"]


def test_parse_empty_text() -> None:
    assert parse_glossary("") == []
