"""A static call graph over the repo's symbols.

For every symbol, we look at the `ast.Call` nodes inside its own source and
check whether the called name matches another symbol we already know about --
`foo(...)` or `x.foo(...)` both count as "calls foo" if some symbol in the
repo is named `foo`. That's plain name-matching, not real type resolution: we
never figure out what `x` actually is, so a common method name shared by two
unrelated classes (`Cart.add` and `Wallet.add`, say) would show call edges to
both. A real static analyzer resolves types to disambiguate; this doesn't,
and that's a deliberate, documented simplification -- for a small single-
language repo, "everything literally named X is treated as one node" gets you
almost all of the value (finding real callers/callees) for a fraction of the
engineering, and it's honest about where it would fall over on a bigger,
noisier codebase.
"""

from __future__ import annotations

import ast
from collections import defaultdict

from .parsing import Symbol


def _called_names(code: str) -> set[str]:
    """Every name a piece of code calls: `foo(...)` -> "foo", `x.foo(...)` -> "foo"."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return set()
    names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name):
            names.add(func.id)
        elif isinstance(func, ast.Attribute):
            names.add(func.attr)
    return names


class CallGraph:
    """Who calls whom, resolved by symbol name within one repo's parsed Symbols."""

    def __init__(self, symbols: list[Symbol]) -> None:
        self.symbols = symbols
        known_names = {s.name for s in symbols}

        self._callees: dict[str, set[str]] = defaultdict(set)
        self._callers: dict[str, set[str]] = defaultdict(set)
        for s in symbols:
            for called in _called_names(s.code):
                if called == s.name or called not in known_names:
                    continue  # skip self-references and anything we don't recognise
                self._callees[s.name].add(called)
                self._callers[called].add(s.name)

    def callers(self, name: str) -> list[str]:
        """Symbol names that call `name`, sorted for stable output."""
        return sorted(self._callers.get(name, ()))

    def callees(self, name: str) -> list[str]:
        """Symbol names that `name` calls, sorted for stable output."""
        return sorted(self._callees.get(name, ()))
