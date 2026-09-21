"""Tests for codeagent.embedding."""

from __future__ import annotations

import numpy as np

from codeagent.embedding import HashingEmbedder, cosine_scores, make_embedder, tokenize


def test_tokenize_splits_snake_case():
    assert tokenize("calculate_shipping") == ["calculate", "shipping"]


def test_tokenize_splits_camel_case():
    toks = tokenize("lineTotal")
    assert "line" in toks
    assert "total" in toks


def test_make_embedder_default_is_hashing():
    embedder = make_embedder()
    assert isinstance(embedder, HashingEmbedder)


def test_fit_transform_unit_normalises_rows():
    embedder = HashingEmbedder(n_features=64)
    vecs = embedder.fit_transform(["shipping cost calculation", "tax rate percentage"])
    norms = np.linalg.norm(vecs, axis=1)
    assert np.allclose(norms[norms > 0], 1.0)


def test_cosine_scores_prefers_matching_text():
    embedder = HashingEmbedder(n_features=256)
    corpus = ["calculate shipping cost for an order", "apply a loyalty points bonus"]
    matrix = embedder.fit_transform(corpus)
    query_vec = embedder.transform(["shipping cost"])[0]
    scores = cosine_scores(matrix, query_vec)
    assert scores[0] > scores[1]
