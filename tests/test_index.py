"""Tests for codeagent.index."""

from __future__ import annotations

from codeagent.index import Hit


def test_search_returns_hits(symbol_index):
    hits = symbol_index.search("shipping cost", k=3)
    assert len(hits) == 3
    assert all(isinstance(h, Hit) for h in hits)
    assert all(h.via == "vector" for h in hits)


def test_search_top_hit_is_relevant(symbol_index):
    # Plain vector search doesn't always put the real implementation first -- a short,
    # keyword-dense wrapper (the `shipping` property, which just calls calculate_shipping)
    # can outrank it, because cosine similarity over a hashed bag-of-words rewards a
    # document where the matching terms are a bigger share of its total content. The
    # honest claim is "it's in the top 3", not "it's always #1" -- and that gap is
    # exactly why graph expansion exists (see test_graph_expansion_recovers_the_real_impl).
    hits = symbol_index.search("shipping cost calculation", k=3)
    assert "calculate_shipping" in {h.chunk.symbol_name for h in hits}


def test_graph_expansion_adds_graph_hits(symbol_index, call_graph):
    hits = symbol_index.search_with_graph_expansion("shipping cost", k=1, graph=call_graph)
    assert any(h.via == "graph" for h in hits)


def test_graph_expansion_recovers_the_real_impl(symbol_index, call_graph):
    # Top-1 plain vector search lands on the `shipping` property (a one-line wrapper),
    # not the `calculate_shipping` function it delegates to. Graph expansion pulls in
    # that function anyway, as a callee of the top hit -- structural context a plain
    # prose-chunk RAG system has no way to know about.
    top1 = symbol_index.search("shipping cost calculation", k=1)
    assert top1[0].chunk.symbol_name != "calculate_shipping"
    expanded = symbol_index.search_with_graph_expansion("shipping cost calculation", k=1, graph=call_graph)
    graph_hits = {h.chunk.symbol_name for h in expanded if h.via == "graph"}
    assert "calculate_shipping" in graph_hits


def test_graph_expansion_without_graph_falls_back_to_vector(symbol_index):
    hits = symbol_index.search_with_graph_expansion("shipping cost", k=3, graph=None)
    assert all(h.via == "vector" for h in hits)
