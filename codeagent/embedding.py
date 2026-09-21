"""Turning code + docstrings into vectors.

Same idea as any semantic search: embed every chunk once, embed the query,
rank by cosine similarity. The default embedder is a from-scratch **hashing**
vectorizer, built with numpy (fit/transform, L2-normalised rows, a plain
dot-product cosine helper) -- offline, deterministic, no network, no model
download.

The one code-specific twist is tokenization: identifiers are not English
prose, so `tokenize` splits `calculate_shipping` into "calculate"/"shipping"
(snake_case) and `lineTotal` into "line"/"total" (camelCase) before hashing,
so a query like "shipping cost" matches the function `calculate_shipping`
even though "shipping" is the only literal substring in common.

An optional `minilm` backend is a lazy import behind a flag for when you want
real sentence embeddings instead.
"""

from __future__ import annotations

import hashlib
import re

import numpy as np

_CAMEL_BOUNDARY_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_WORD_RE = re.compile(r"[A-Za-z0-9]+")


def tokenize(text: str) -> list[str]:
    """Split code/docstring text into lowercase word tokens.

    `[A-Za-z0-9]+` already splits on underscores (snake_case), and inserting a
    space before each new capital letter splits camelCase the same way, so
    both naming conventions come out as their component English words.
    """
    tokens: list[str] = []
    for raw in _WORD_RE.findall(text):
        for piece in _CAMEL_BOUNDARY_RE.sub(" ", raw).split():
            tokens.append(piece.lower())
    return tokens


class HashingEmbedder:
    """A from-scratch hashing vectorizer: hash each token into a fixed-size bucket.

    There's no vocabulary to fit (that's the point of hashing -- new tokens at
    query time just hash into an existing bucket), but `fit` still records how
    many chunks each bucket appears in, so common buckets (things like "self"
    or "return" that show up in nearly every chunk) get downweighted the same
    way IDF downweights common words in TF-IDF.
    """

    def __init__(self, n_features: int = 512) -> None:
        self.n_features = n_features
        self.doc_freq: np.ndarray | None = None
        self.n_docs = 0
        self.name = "hashing"

    def _bucket(self, token: str) -> int:
        digest = hashlib.md5(token.encode("utf-8")).hexdigest()
        return int(digest, 16) % self.n_features

    def fit(self, corpus: list[str]) -> "HashingEmbedder":
        self.n_docs = len(corpus)
        df = np.zeros(self.n_features, dtype=np.float64)
        for text in corpus:
            for bucket in {self._bucket(t) for t in tokenize(text)}:
                df[bucket] += 1
        self.doc_freq = df
        return self

    def transform(self, texts: list[str]) -> np.ndarray:
        """Turn texts into an (n_texts, n_features) matrix of L2-normalised vectors."""
        assert self.doc_freq is not None, "call fit() first"
        idf = np.log((1 + self.n_docs) / (1 + self.doc_freq)) + 1
        rows = np.zeros((len(texts), self.n_features), dtype=np.float64)
        for r, text in enumerate(texts):
            toks = tokenize(text)
            if not toks:
                continue
            for t in toks:
                rows[r, self._bucket(t)] += 1
            rows[r] = (rows[r] / len(toks)) * idf
        norms = np.linalg.norm(rows, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return rows / norms

    def fit_transform(self, corpus: list[str]) -> np.ndarray:
        return self.fit(corpus).transform(corpus)


class MiniLMEmbedder:
    """Optional real sentence embeddings via sentence-transformers (a download the first time)."""

    def __init__(self, model: str = "all-MiniLM-L6-v2") -> None:
        from sentence_transformers import SentenceTransformer  # noqa: PLC0415 (lazy)

        self._model = SentenceTransformer(model)
        self.name = "minilm"

    def fit(self, corpus: list[str]) -> "MiniLMEmbedder":
        return self  # nothing to fit; the model is pretrained

    def transform(self, texts: list[str]) -> np.ndarray:
        vecs = self._model.encode(texts, normalize_embeddings=True)
        return np.asarray(vecs, dtype=np.float64)

    def fit_transform(self, corpus: list[str]) -> np.ndarray:
        return self.transform(corpus)


def make_embedder(kind: str = "hashing"):
    """Pick an embedder: 'hashing' (default, offline) or 'minilm' (real, opt-in download)."""
    if kind == "minilm":
        return MiniLMEmbedder()
    return HashingEmbedder()


def cosine_scores(matrix: np.ndarray, query_vec: np.ndarray) -> np.ndarray:
    """Cosine similarity of every row in `matrix` against `query_vec` (both unit-normalised)."""
    return matrix @ query_vec
