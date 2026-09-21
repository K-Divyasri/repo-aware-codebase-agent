"""The five tools the agent can call, plus their Anthropic tool-use schemas.

A "tool" here is a plain Python function; the model never runs code itself,
it only ever *asks* for a tool by name with some JSON arguments, and this
project's code actually runs it and hands the result back. Each function below
takes the live sandbox/index/graph objects as ordinary arguments (not global
state), so a test can build a fresh Sandbox + SymbolIndex and call any tool
directly with no agent involved.

`TOOL_SCHEMAS` uses Anthropic's native tool shape --
`{"name", "description", "input_schema"}` -- because `agent.py`'s real mode
calls `anthropic.Anthropic().messages.create(..., tools=TOOL_SCHEMAS)`
directly (see that module's docstring for why this project doesn't go through
a provider-agnostic layer here).

`ToolRunner` is a thin per-session wrapper: it closes over one Sandbox,
SymbolIndex, and CallGraph and exposes a single `dispatch(name, input)` method,
so the agent loop (offline or real) can call tools generically by name without
knowing which Python function backs which string.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .diffing import write_file
from .graph import CallGraph
from .index import SymbolIndex
from .sandbox import Sandbox
from .sandbox import run_tests as _run_tests_impl


def list_files(repo_path: Path, pattern: str = "**/*.py") -> list[str]:
    """List files under `repo_path` matching a glob pattern, as repo-relative posix paths."""
    root = Path(repo_path)
    return sorted(
        p.relative_to(root).as_posix()
        for p in root.glob(pattern)
        if p.is_file() and "__pycache__" not in p.parts
    )


def read_file(repo_path: Path, path: str, start_line: int | None = None, end_line: int | None = None) -> str:
    """Read a file's text with `NNN| ` line-number prefixes, optionally sliced by line range."""
    target = Path(repo_path) / path
    if not target.exists():
        return f"Error: no such file '{path}'."
    lines = target.read_text(encoding="utf-8").splitlines()
    start = start_line or 1
    end = end_line or len(lines)
    numbered = [f"{i:>4}| {line}" for i, line in enumerate(lines, start=1) if start <= i <= end]
    return "\n".join(numbered)


def search_code(index: SymbolIndex, graph: CallGraph, query: str, k: int = 5) -> list[dict]:
    """Search the symbol index (with graph expansion) and return plain-dict hits."""
    hits = index.search_with_graph_expansion(query, k=k, graph=graph)
    results = []
    for h in hits:
        snippet = h.chunk.text.strip()[:200].replace("\n", " ")
        results.append(
            {
                "symbol": h.chunk.symbol_name,
                "kind": h.chunk.kind,
                "file": h.chunk.file,
                "lineno": h.chunk.lineno,
                "score": round(h.score, 4),
                "via": h.via,
                "callers": h.chunk.callers,
                "callees": h.chunk.callees,
                "snippet": snippet,
            }
        )
    return results


def run_tests(repo_path: Path, test_path: str | None = None) -> dict:
    """Run the repo's test suite and return a plain dict of the result."""
    result = _run_tests_impl(repo_path, test_path=test_path)
    return {
        "passed": result.passed,
        "failed": result.failed,
        "total": result.total,
        "failures": result.failures,
    }


def propose_fix(repo_path: Path, file: str, new_content: str) -> dict:
    """Write `new_content` into `file` (in the sandbox) and return `{"diff": ...}`."""
    diff = write_file(repo_path, file, new_content)
    return {"diff": diff}


TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "name": "list_files",
        "description": (
            "List Python files in the repo matching a glob pattern. Use this to see what's "
            "in the codebase before reading anything."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Glob pattern to match, e.g. '**/*.py' (the default) or 'cartlogic/*.py'.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "read_file",
        "description": (
            "Read a file's contents with line-number prefixes. Use this to inspect a specific "
            "file before proposing a fix."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Repo-relative file path, e.g. 'cartlogic/shipping.py'."},
                "start_line": {"type": "integer", "description": "First line to include (1-based, optional)."},
                "end_line": {"type": "integer", "description": "Last line to include (optional)."},
            },
            "required": ["path"],
        },
    },
    {
        "name": "search_code",
        "description": (
            "Semantic search over the repo's functions/classes/methods, expanded with their "
            "direct callers and callees from the call graph. Use this to find where something "
            "is implemented or what depends on it."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "What to search for, e.g. 'shipping cost calculation'."},
                "k": {"type": "integer", "description": "How many top vector hits to expand from (default 5)."},
            },
            "required": ["query"],
        },
    },
    {
        "name": "run_tests",
        "description": (
            "Run the repo's pytest suite (or one file/path within it) and get pass/fail counts "
            "plus the names of any failing tests."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "test_path": {
                    "type": "string",
                    "description": "A specific test file or path to run, e.g. 'tests/test_shipping.py' (default: the whole 'tests' folder).",
                },
            },
            "required": [],
        },
    },
    {
        "name": "propose_fix",
        "description": (
            "Write new content to a file in the sandbox and get back a unified diff against "
            "what was there before. This is how a fix is actually applied."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "file": {"type": "string", "description": "Repo-relative path of the file to modify."},
                "new_content": {"type": "string", "description": "The full new contents of the file."},
            },
            "required": ["file", "new_content"],
        },
    },
]


class ToolRunner:
    """Closes over one live Sandbox/SymbolIndex/CallGraph so the agent can dispatch by name alone."""

    def __init__(self, sandbox: Sandbox, index: SymbolIndex, graph: CallGraph) -> None:
        self.sandbox = sandbox
        self.index = index
        self.graph = graph

    def dispatch(self, name: str, input: dict) -> dict:
        """Run the named tool with `input` and return its plain-dict result."""
        repo_path = self.sandbox.path
        if name == "list_files":
            return {"files": list_files(repo_path, **input)}
        if name == "read_file":
            return {"text": read_file(repo_path, **input)}
        if name == "search_code":
            return {"hits": search_code(self.index, self.graph, **input)}
        if name == "run_tests":
            return run_tests(repo_path, **input)
        if name == "propose_fix":
            return propose_fix(repo_path, **input)
        return {"error": f"unknown tool '{name}'"}
