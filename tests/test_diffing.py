"""Tests for codeagent.diffing."""

from __future__ import annotations

from codeagent.diffing import unified_diff, write_file
from codeagent.sandbox import Sandbox


def test_unified_diff_shows_the_changed_line():
    diff = unified_diff("a\nb\nc\n", "a\nX\nc\n", "f.py")
    assert "-b" in diff
    assert "+X" in diff


def test_unified_diff_no_changes_is_empty():
    assert unified_diff("same\n", "same\n", "f.py") == ""


def test_write_file_updates_sandbox_and_returns_diff():
    with Sandbox() as sandbox:
        original = (sandbox.path / "cartlogic" / "loyalty.py").read_text(encoding="utf-8")
        new_content = original.replace("int(total // 1)", "round(total)")
        diff = write_file(sandbox.path, "cartlogic/loyalty.py", new_content)
        assert "round(total)" in diff
        assert (sandbox.path / "cartlogic" / "loyalty.py").read_text(encoding="utf-8") == new_content
