"""Tests for codeagent.eval: the offline agent should pass every eval task."""

from __future__ import annotations

from codeagent.eval import run_eval


def test_run_eval_all_tasks_pass():
    report = run_eval(real=False)
    assert report.n_passed == len(report.reports)
    for r in report.reports:
        assert r.passed, f"{r.task_id} failed: {r.detail}"


def test_eval_report_table_mentions_every_task():
    report = run_eval(real=False)
    table = report.table()
    for r in report.reports:
        assert r.task_id in table
