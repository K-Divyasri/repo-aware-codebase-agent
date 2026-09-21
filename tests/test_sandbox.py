"""Tests for codeagent.sandbox."""

from __future__ import annotations

from codeagent.sandbox import Sandbox, TestResult, run_tests


def test_sandbox_copies_target_repo():
    with Sandbox() as sandbox:
        assert sandbox.path.exists()
        assert (sandbox.path / "cartlogic" / "shipping.py").exists()
        assert sandbox.path != sandbox.source


def test_sandbox_is_disposed_after_context():
    with Sandbox() as sandbox:
        path = sandbox.path
    assert not path.exists()


def test_editing_sandbox_does_not_touch_original():
    with Sandbox() as sandbox:
        target = sandbox.path / "cartlogic" / "shipping.py"
        target.write_text("ruined", encoding="utf-8")
        source_ref = sandbox.source
    real_source_file = source_ref / "cartlogic" / "shipping.py"
    assert "ruined" not in real_source_file.read_text(encoding="utf-8")


def test_run_tests_reports_five_known_failures():
    with Sandbox() as sandbox:
        result = run_tests(sandbox.path)
    assert isinstance(result, TestResult)
    assert result.failed == 5
    assert result.passed == 15
    assert result.total == 20
    assert len(result.failures) == 5


def test_run_tests_can_target_one_file():
    with Sandbox() as sandbox:
        result = run_tests(sandbox.path, test_path="tests/test_shipping.py")
    assert result.total == 4
    assert result.failed == 1
