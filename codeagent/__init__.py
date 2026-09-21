"""codeagent: a repo-aware agent over an AST-parsed Python codebase.

Parses a real repo's symbols and call graph via the stdlib `ast` module (not
prose chunking), indexes them for search, runs the repo's tests in a
disposable sandbox, and proposes diffs to fix bugs -- offline by default, with
an optional real Claude tool-use loop.
"""

from __future__ import annotations

from .agent import AgentResult, CodebaseAgent, KNOWN_FIXES
from .chunking import Chunk, build_chunks
from .embedding import HashingEmbedder, MiniLMEmbedder, make_embedder
from .eval import EvalReport, TASKS, TaskReport, run_eval
from .graph import CallGraph
from .index import Hit, SymbolIndex
from .parsing import Symbol, parse_file, parse_repo, parse_repo_treesitter
from .sandbox import Sandbox, TestResult, run_tests
from .tools import TOOL_SCHEMAS, ToolRunner

__all__ = [
    "AgentResult",
    "CodebaseAgent",
    "KNOWN_FIXES",
    "Chunk",
    "build_chunks",
    "HashingEmbedder",
    "MiniLMEmbedder",
    "make_embedder",
    "EvalReport",
    "TASKS",
    "TaskReport",
    "run_eval",
    "CallGraph",
    "Hit",
    "SymbolIndex",
    "Symbol",
    "parse_file",
    "parse_repo",
    "parse_repo_treesitter",
    "Sandbox",
    "TestResult",
    "run_tests",
    "TOOL_SCHEMAS",
    "ToolRunner",
]
