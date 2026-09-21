"""Tests for the offline CodebaseAgent: all 5 known fixes, plus the explain fallback."""

from __future__ import annotations

import pytest

from codeagent.agent import CodebaseAgent
from codeagent.sandbox import Sandbox, run_tests

FIX_TASKS = [
    ("The shipping tests are failing, please fix it.", "tests/test_shipping.py"),
    ("The tax tests are failing, please fix it.", "tests/test_tax.py"),
    ("The bulk discount tests are failing, please fix it.", "tests/test_discounts.py"),
    ("The cart total tests are failing, please fix it.", "tests/test_cart.py"),
    ("The loyalty points tests are failing, please fix it.", "tests/test_loyalty.py"),
]


@pytest.mark.parametrize("task,check_path", FIX_TASKS)
def test_offline_fix_turns_target_tests_green(task, check_path):
    with Sandbox() as sandbox:
        agent = CodebaseAgent(sandbox)
        result = agent.run(task, real=False)
        assert result.success
        assert result.diff
        after = run_tests(sandbox.path, test_path=check_path)
        assert after.failed == 0
        assert after.total > 0


def test_offline_explain_fallback_names_top_symbol():
    with Sandbox() as sandbox:
        agent = CodebaseAgent(sandbox)
        result = agent.run("Where is shipping cost calculated and what does it depend on?", real=False)
        assert result.diff is None
        assert "calculate_shipping" in result.final_message
        assert "shipping.py" in result.final_message


def test_offline_agent_result_has_before_and_after_counts():
    with Sandbox() as sandbox:
        agent = CodebaseAgent(sandbox)
        result = agent.run("The loyalty points tests are failing, please fix it.", real=False)
        assert result.tests_before.failed == 5
        assert result.tests_after.failed == 4


def test_offline_fix_produces_a_tool_trace():
    with Sandbox() as sandbox:
        agent = CodebaseAgent(sandbox)
        result = agent.run("The tax tests are failing, please fix it.", real=False)
        tool_names = [step["tool"] for step in result.tool_trace]
        assert "read_file" in tool_names
        assert "propose_fix" in tool_names
        assert "run_tests" in tool_names
