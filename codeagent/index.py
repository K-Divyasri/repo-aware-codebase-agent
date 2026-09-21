"""The symbol index: embed every chunk once, search by cosine similarity, and
optionally expand hits across the call graph.

Plain vector search finds chunks whose TEXT resembles the query -- that's
standard semantic search, no different from searching movie descriptions or
support articles. The graph-expansion pass is this project's actual point:
once we have the top vector hits, we also pull in their direct callers and
callees from the `CallGraph`, because "what calls this" and "what does this
call" is exactly the context a human (or an LLM) needs to reason about a bug,
and plain prose-chunk RAG has no way to know that at all -- there is no call
graph hiding in a paragraph of text. Hits gained through the graph are tagged
`via="graph"`; ordinary vector hits are `via="vector"`, so a caller can always
tell how a piece of context was found.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .chunking import Chunk
from .embedding import cosine_scores
from .graph import CallGraph


@dataclass
class Hit:
    """One retrieved chunk, its similarity score, and how it was found."""

    chunk: Chunk
    score: float
    via: str  # "vector" | "graph"


class SymbolIndex:
    """Fitted embeddings over a repo's Chunks, searchable by cosine similarity."""

    def __init__(self, chunks: list[Chunk], embedder, vectors: np.ndarray) -> None:
        self.chunks = chunks
        self.embedder = embedder
        self.vectors = vectors
        self._by_name: dict[str, Chunk] = {c.symbol_name: c for c in chunks}

    @classmethod
    def build(cls, chunks: list[Chunk], embedder) -> "SymbolIndex":
        """Fit the embedder on every chunk's text and store the resulting vectors."""
        texts = [c.text for c in chunks]
        vectors = embedder.fit_transform(texts)
        return cls(chunks, embedder, vectors)

    def search(self, query: str, k: int = 5) -> list[Hit]:
        """Plain vector search: the k chunks whose text is most similar to `query`."""
        if not self.chunks:
            return []
        query_vec = self.embedder.transform([query])[0]
        scores = cosine_scores(self.vectors, query_vec)
        order = np.argsort(-scores)[:k]
        return [Hit(chunk=self.chunks[i], score=float(scores[i]), via="vector") for i in order]

    def search_with_graph_expansion(self, query: str, k: int = 5, graph: CallGraph | None = None) -> list[Hit]:
        """Vector search, then add each top hit's direct callers/callees as extra context.

        This is the retrieval strategy that actually distinguishes a repo-
        aware agent from a prose-RAG one: the extra hits didn't score well on
        text similarity, they're included because the call graph says they're
        structurally connected to something that did.
        """
        hits = self.search(query, k=k)
        if graph is None:
            return hits
        seen = {h.chunk.symbol_name for h in hits}
        expanded = list(hits)
        for h in hits:
            neighbors = graph.callers(h.chunk.symbol_name) + graph.callees(h.chunk.symbol_name)
            for name in neighbors:
                if name in seen:
                    continue
                seen.add(name)
                chunk = self._by_name.get(name)
                if chunk is None:
                    continue
                expanded.append(Hit(chunk=chunk, score=0.0, via="graph"))
        return expanded
