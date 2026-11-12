"""CLI to review chunk quality: ``python -m app.retrieval.inspect_chunks [file]``.

Prints each chunk's id, token size and section path so chunk boundaries can be
reviewed by eye. ``file`` may be a full file name (e.g. ``dailymed-warfarin.md``)
or any sub-string of it (e.g. a drug name), matching every chunk whose
``source_file`` contains it.
"""

from __future__ import annotations

import sys
from pathlib import Path

from app.core.config import get_settings
from app.retrieval.chunker import chunk_document
from app.retrieval.loader import load_documents


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    settings = get_settings()
    corpus_dir = Path(settings.corpus_dir)

    documents = load_documents(corpus_dir)
    chunks_by_file = {
        document.source_file: chunk_document(
            document,
            max_tokens=settings.chunk_max_tokens,
            overlap_tokens=settings.chunk_overlap_tokens,
            chars_per_token=settings.chars_per_token,
        )
        for document in documents
    }
    titles = {document.source_file: document.title for document in documents}

    needle = args[0].lower() if args else None
    total = sum(len(chunks) for chunks in chunks_by_file.values())
    print(f"corpus: {corpus_dir} ({len(documents)} documents, {total} chunks)")
    if needle:
        print(f"filter: {needle!r}")

    for source_file, chunks in sorted(chunks_by_file.items()):
        if needle and needle not in source_file.lower():
            continue
        print(f"\n-- {source_file} ({titles[source_file]}) -- {len(chunks)} chunks")
        for chunk in chunks:
            print(f"{chunk.chunk_id}  {chunk.token_count:>5}t  {chunk.section_path}")


if __name__ == "__main__":
    main()
