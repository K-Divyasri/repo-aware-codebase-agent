"""A tiny eval harness: 6 tasks, a fresh sandbox each, a pass/fail scorecard.

Five "fix" tasks (one per seeded bug in `data/target_repo`) and one "explain"
task, so both agent behaviors -- fixing a known bug and answering a locate/
explain question -- are actually checked, not just exercised. Each task runs
against its OWN fresh `Sandbox`, so a fix applied for one task can never leak
into another task's run.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .agent import CodebaseAgent
from .sandbox import Sandbox
from .sandbox import run_tests as _run_tests

TASKS: list[dict] = [
    {
        "id": "fix_shipping",
        "prompt": "The shipping tests are failing, please fix it.",
        "kind": "fix",
        "check_tests": "tests/test_shipping.py",
    },
    {
        "id": "fix_tax",
        "prompt": "The tax tests are failing, please fix it.",
        "kind": "fix",
        "check_tests": "tests/test_tax.py",
    },
    {
        "id": "fix_discounts",
        "prompt": "The bulk discount tests are failing, please fix it.",
        "kind": "fix",
        "check_tests": "tests/test_discounts.py",
    },
    {
        "id": "fix_cart",
        "prompt": "The cart total tests are failing, please fix it.",
        "kind": "fix",
        "check_tests": "tests/test_cart.py",
    },
    {
        "id": "fix_loyalty",
        "prompt": "The loyalty points tests are failing, please fix it.",
        "kind": "fix",
        "check_tests": "tests/test_loyalty.py",
    },
    {
        "id": "explain_shipping",
        "prompt": "Where is shipping cost calculated and what does it depend on?",
        "kind": "explain",
        "check_terms": ["shipping.py", "free_shipping_threshold"],
    },
]


@dataclass
class TaskReport:
    """One task's outcome: whether it passed, how many tool turns it took, and why."""

    task_id: str
    passed: bool
    turns: int
    detail: str = ""


@dataclass
class EvalReport:
    """The full scorecard across all TASKS."""

    reports: list[TaskReport] = field(default_factory=list)

    @property
    def n_passed(self) -> int:
        return sum(1 for r in self.reports if r.passed)

    def table(self) -> str:
        """A plain-text scorecard: task id, pass/fail, turns used, and a short detail."""
        header = f"{'task':<18} {'passed':<8} {'turns':<6} detail"
        rule = "-" * max(len(header), 40)
        lines = [header, rule]
        for r in self.reports:
            lines.append(f"{r.task_id:<18} {str(r.passed):<8} {r.turns:<6} {r.detail}")
        lines.append(rule)
        lines.append(f"{self.n_passed}/{len(self.reports)} tasks passed")
        return "\n".join(lines)


def run_eval(*, real: bool = False) -> EvalReport:
    """Run every task in TASKS against a fresh Sandbox and score the outcome."""
    reports = []
    for task in TASKS:
        with Sandbox() as sandbox:
            agent = CodebaseAgent(sandbox)
            result = agent.run(task["prompt"], real=real)
            turns = len(result.tool_trace)
            if task["kind"] == "fix":
                check = _run_tests(sandbox.path, test_path=task["check_tests"])
                passed = check.total > 0 and check.failed == 0
                detail = f"{check.passed}/{check.total} tests passing"
            else:
                terms = task["check_terms"]
                message_lower = result.final_message.lower()
                missing = [t for t in terms if t.lower() not in message_lower]
                passed = not missing
                detail = "all terms found" if passed else f"missing: {', '.join(missing)}"
            reports.append(TaskReport(task_id=task["id"], passed=passed, turns=turns, detail=detail))
    return EvalReport(reports=reports)
