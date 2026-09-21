"""Turn parsed Symbols + the call graph into indexable Chunks.

One Chunk per symbol. `text` is what actually gets embedded -- docstring
first, then code, so a search query matches either the plain-English intent
("shipping cost") or the identifiers/keywords themselves. Each chunk also
carries its direct callers/callees from the CallGraph as metadata, so once a
chunk is retrieved, the caller already knows what depends on it and what it
depends on without a second lookup -- that metadata is what `index.py`'s
graph-expansion search actually walks.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .graph import CallGraph
from .parsing import Symbol


@dataclass
class Chunk:
    """One embeddable, retrievable unit: a symbol plus its text and graph neighbors."""

    chunk_id: str
    symbol_name: str
    kind: str
    file: str
    text: str
    lineno: int
    end_lineno: int
    callers: list[str] = field(default_factory=list)
    callees: list[str] = field(default_factory=list)


def build_chunks(symbols: list[Symbol], graph: CallGraph) -> list[Chunk]:
    """Build one Chunk per symbol, embedding text and graph neighbors included."""
    chunks = []
    for s in symbols:
        chunk_id = f"{s.file}:{s.qualname}:{s.lineno}"
        text = f"{s.docstring}\n\n{s.code}" if s.docstring else s.code
        chunks.append(
            Chunk(
                chunk_id=chunk_id,
                symbol_name=s.name,
                kind=s.kind,
                file=s.file,
                text=text,
                lineno=s.lineno,
                end_lineno=s.end_lineno,
                callers=graph.callers(s.name),
                callees=graph.callees(s.name),
            )
        )
    return chunks
