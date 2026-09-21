"""Unified diffs: a proposed fix is only useful if a human (or the eval
harness) can see exactly what changed.

`unified_diff` wraps `difflib.unified_diff` in the familiar `---`/`+++`/`@@`
text format. `write_file` actually writes into a sandbox copy and returns the
diff against whatever was there before -- the agent never edits blind; every
`propose_fix` call comes back with something reviewable.
"""

from __future__ import annotations

import difflib
from pathlib import Path


def unified_diff(original_text: str, new_text: str, path: str) -> str:
    """A unified diff string between two versions of a file's text."""
    diff = difflib.unified_diff(
        original_text.splitlines(keepends=True),
        new_text.splitlines(keepends=True),
        fromfile=f"a/{path}",
        tofile=f"b/{path}",
    )
    return "".join(diff)


def write_file(repo_path: Path, relpath: str, new_content: str) -> str:
    """Write `new_content` to `repo_path/relpath` (a sandbox copy) and return the unified diff."""
    target = Path(repo_path) / relpath
    original = target.read_text(encoding="utf-8") if target.exists() else ""
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(new_content, encoding="utf-8")
    return unified_diff(original, new_content, relpath)
