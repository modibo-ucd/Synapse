"""A small, dependency-free BM25 implementation.

The tokenizer keeps numbers, units and abbreviations intact (``30``, ``1.73``,
``mL/min``, ``INR``), lowercases input and drops punctuation. Ranking uses the
standard BM25 scoring function with configurable ``k1`` and ``b``.
"""

from __future__ import annotations

import math
import re
from collections import Counter

_TOKEN_RE = re.compile(r"[a-z0-9]+(?:[./][a-z0-9]+)*")


def tokenize(text: str) -> list[str]:
    """Lowercase and split into word/number/unit tokens."""
    return _TOKEN_RE.findall(text.lower())


class BM25Index:
    """BM25 ranking over an in-memory corpus of documents."""

    def __init__(
        self,
        documents: list[str] | None = None,
        *,
        k1: float = 1.2,
        b: float = 0.75,
    ) -> None:
        self._k1 = k1
        self._b = b
        self._docs: list[list[str]] = []
        self._doc_len: list[int] = []
        self._doc_freq: list[Counter[str]] = []
        self._df: Counter[str] = Counter()
        self._avgdl = 0.0
        if documents is not None:
            self.fit(documents)

    def fit(self, documents: list[str]) -> None:
        """Tokenize the corpus and compute document frequencies and lengths."""
        self._docs = [tokenize(document) for document in documents]
        self._doc_len = [len(tokens) for tokens in self._docs]
        self._doc_freq = [Counter(tokens) for tokens in self._docs]
        self._df = Counter()
        for freq in self._doc_freq:
            self._df.update(freq.keys())
        self._avgdl = sum(self._doc_len) / len(self._docs) if self._docs else 0.0

    def __len__(self) -> int:
        return len(self._docs)

    def search(self, query: str, k: int = 10) -> list[tuple[int, float]]:
        """Return the top-k ``(document_index, score)`` pairs for a query."""
        if not self._docs or k <= 0:
            return []
        query_terms = tokenize(query)
        scored: list[tuple[int, float]] = []
        for index, freq in enumerate(self._doc_freq):
            score = 0.0
            norm = 1.0 - self._b + self._b * (self._doc_len[index] / self._avgdl)
            for term in query_terms:
                df = self._df.get(term, 0)
                tf = freq.get(term, 0)
                if df == 0 or tf == 0:
                    continue
                idf = math.log(1.0 + (len(self._docs) - df + 0.5) / (df + 0.5))
                score += idf * (tf * (self._k1 + 1.0)) / (tf + self._k1 * norm)
            if score > 0.0:
                scored.append((index, score))
        scored.sort(key=lambda item: item[1], reverse=True)
        return scored[:k]
