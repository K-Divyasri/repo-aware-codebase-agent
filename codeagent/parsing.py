"""AST-based parsing: turn Python source files into a flat list of Symbols.

A "symbol" here is one function, method, or class -- the unit a codebase-aware
agent actually reasons about ("fix `calculate_shipping`", not "fix line 400 of
some 2000-line file"). The default (and only real) backend uses Python's own
`ast` module: `ast.parse` the file, walk the tree, and pull out the exact
source text of each def/class with `ast.get_source_segment`. That's it -- no
external parser, no network, no install beyond the standard library. The
stdlib option is not a placeholder, it's the real default, and it's exactly
right for a single-language Python repo like the toy `cartlogic` codebase this
project ships with.

Multi-language repos (JS, Go, Rust, ...) need a real parser per language --
that's what `tree-sitter` is for. `parse_repo_treesitter` is a deliberately
minimal stub documenting that upgrade path without requiring the dependency.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Symbol:
    """One function, method, or class pulled out of a Python file."""

    name: str
    kind: str  # "function" | "method" | "class"
    file: str
    lineno: int
    end_lineno: int
    code: str
    docstring: str
    qualname: str


class _SymbolVisitor(ast.NodeVisitor):
    """Walks a module, tracking class nesting so methods vs functions are told apart."""

    def __init__(self, source: str, file: str) -> None:
        self.source = source
        self.file = file
        self.symbols: list[Symbol] = []
        self._class_stack: list[str] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._emit(node, "class")
        self._class_stack.append(node.name)
        self.generic_visit(node)
        self._class_stack.pop()

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        kind = "method" if self._class_stack else "function"
        self._emit(node, kind)
        self.generic_visit(node)

    visit_FunctionDef = _visit_function
    visit_AsyncFunctionDef = _visit_function

    def _emit(self, node: ast.AST, kind: str) -> None:
        code = ast.get_source_segment(self.source, node) or ""
        docstring = ast.get_docstring(node) or ""
        qualname = ".".join([*self._class_stack, node.name])
        self.symbols.append(
            Symbol(
                name=node.name,
                kind=kind,
                file=self.file,
                lineno=node.lineno,
                end_lineno=node.end_lineno or node.lineno,
                code=code,
                docstring=docstring,
                qualname=qualname,
            )
        )


def parse_file(path: Path) -> list[Symbol]:
    """Parse one Python file into a list of Symbols (empty list on a syntax error).

    `Symbol.file` is set to `str(path)` exactly as given -- if you want repo-
    relative paths and module-qualified names, drive this through `parse_repo`,
    which normalises both after the fact.
    """
    path = Path(path)
    source = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        return []
    visitor = _SymbolVisitor(source, str(path))
    visitor.visit(tree)
    return visitor.symbols


def _module_name(path: Path, root: Path) -> str:
    """Dotted module path for a file relative to a repo root, e.g. cartlogic/cart.py -> cartlogic.cart."""
    parts = list(path.relative_to(root).with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def parse_repo(root: Path, *, include_tests: bool = False) -> list[Symbol]:
    """Parse every `.py` file under `root` (skipping `__pycache__`) into Symbols.

    Rewrites each Symbol's `file` to a repo-relative, forward-slash path and
    prefixes `qualname` with the file's dotted module name, so `Cart.total`
    becomes `cartlogic.cart.Cart.total` -- unambiguous even across files that
    happen to define same-named classes or methods.

    `tests/` is skipped by default. A "chat with the codebase" search is meant
    to find where something is *implemented*; a bare `assert calculate_shipping(0.0)
    == 5.99` is short, keyword-dense, and otherwise indistinguishable from real
    source to a bag-of-words embedder, so left in it tends to outrank the actual
    function it's testing. The test suite is still fully reachable through the
    `run_tests` tool -- it's just not part of the searchable symbol index. Pass
    `include_tests=True` if you deliberately want tests searchable too.
    """
    root = Path(root)
    symbols: list[Symbol] = []
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        if not include_tests and ("tests" in path.parts or path.name.startswith("test_")):
            continue
        file_symbols = parse_file(path)
        rel = path.relative_to(root).as_posix()
        module = _module_name(path, root)
        for s in file_symbols:
            s.file = rel
            s.qualname = f"{module}.{s.qualname}" if module else s.qualname
        symbols.extend(file_symbols)
    return symbols


def parse_repo_treesitter(root: Path) -> list[Symbol]:  # pragma: no cover - documented stub only
    """Multi-language parsing via tree-sitter. NOT implemented -- a stub for the upgrade path.

    The stdlib `ast` backend above only understands Python, which is fine for
    this project's target repo but not for a real polyglot codebase. Swapping
    in tree-sitter (with per-language grammars via `tree_sitter_languages`)
    would let `parse_repo` walk JS/Go/Rust/etc. files too. That's a real chunk
    of work -- wiring up grammars, query patterns per language, matching node
    types back to Symbol.kind -- so rather than fake it, this stays an honest
    stub gated behind the optional `treesitter` extra
    (`pip install -e .[treesitter]`).
    """
    try:
        import tree_sitter  # noqa: F401
    except ImportError as exc:
        raise NotImplementedError(
            "parse_repo_treesitter needs the optional `treesitter` extra: "
            "pip install -e .[treesitter]  (tree_sitter + tree_sitter_languages). "
            "Even with it installed, no language grammars are wired up here -- "
            "see this function's docstring."
        ) from exc
    raise NotImplementedError(
        "tree_sitter is installed, but this project does not wire up any language "
        "grammars -- this stub only documents where that work would go."
    )
