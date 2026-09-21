"""Tests for codeagent.chunking."""

from __future__ import annotations

from codeagent.chunking import Chunk, build_chunks


def test_build_chunks_one_per_symbol(repo_symbols, call_graph):
    chunks = build_chunks(repo_symbols, call_graph)
    assert len(chunks) == len(repo_symbols)
    assert all(isinstance(c, Chunk) for c in chunks)


def test_chunk_text_includes_docstring_and_code(symbol_index):
    chunk = next(c for c in symbol_index.chunks if c.symbol_name == "calculate_shipping")
    assert "shipping fee" in chunk.text.lower()
    assert "def calculate_shipping" in chunk.text


def test_chunk_carries_graph_neighbors(symbol_index):
    chunk = next(c for c in symbol_index.chunks if c.symbol_name == "shipping")
    assert "calculate_shipping" in chunk.callees
