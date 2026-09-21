"""A disposable sandbox copy of the target repo, plus running its test suite.

SAFETY GUARANTEE: every agent run works on a throwaway `tempfile.mkdtemp()`
copy of `data/target_repo`, never the original. If the agent proposes a bad
edit, or a test run leaves stray files behind, the real target repo on disk is
untouched -- exit the `with Sandbox()` block (or let it go out of scope) and
the copy is deleted. That's the same guarantee you'd want from any real "let
an LLM edit your code" tool: never let the model near the one copy of the repo
you actually care about.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path


def _find_target_repo() -> Path:
    """Walk up from this file to the project folder containing data/target_repo.

    Climbs `__file__`'s parents until one of them contains the folder we're
    looking for, so it works from wherever the package is run.
    """
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "data" / "target_repo"
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        "Could not find data/target_repo above codeagent/sandbox.py. "
        "Run generate_target_repo.py from the project root first."
    )


@dataclass
class TestResult:
    """A parsed pytest run: counts, which tests failed, and the raw output."""

    __test__ = False  # tell pytest this is a plain dataclass, not a test class to collect

    passed: int
    failed: int
    total: int
    failures: list[str] = field(default_factory=list)
    raw_output: str = ""


class Sandbox:
    """A fresh, disposable copy of data/target_repo. A context manager: use `with Sandbox() as sb:`."""

    def __init__(self, source: Path | None = None) -> None:
        self.source = Path(source) if source else _find_target_repo()
        self.path: Path | None = None
        self._tmpdir: Path | None = None

    def __enter__(self) -> "Sandbox":
        self._tmpdir = Path(tempfile.mkdtemp(prefix="codeagent_sandbox_"))
        self.path = self._tmpdir / self.source.name
        shutil.copytree(self.source, self.path)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._tmpdir is not None:
            shutil.rmtree(self._tmpdir, ignore_errors=True)


_FAILED_COUNT_RE = re.compile(r"(\d+) failed")
_PASSED_COUNT_RE = re.compile(r"(\d+) passed")
_FAILURE_LINE_RE = re.compile(r"^FAILED (\S+)", re.MULTILINE)


def run_tests(repo_path: Path, test_path: str | None = None, timeout: int = 30) -> TestResult:
    """Run pytest inside `repo_path` and parse its plain-text summary.

    `repo_path` should always be a Sandbox's `.path` (the disposable copy),
    never `data/target_repo` itself -- this function doesn't enforce that,
    but every caller in this project only ever passes a sandbox path.

    Runs `python -m pytest -q --color=no <test_path or "tests">` as a subprocess and reads
    pytest's own summary line ("3 failed, 12 passed in 0.1s") and "FAILED
    path::test" lines -- no extra plugins, no JSON report, just stable,
    version-independent plain text.

    `--color=no` is not cosmetic: pytest auto-detects color support from the
    calling environment, and some environments (e.g. a subprocess spawned from
    inside a Jupyter kernel) make it emit ANSI escape codes even though
    `capture_output=True` means nothing is ever displayed on a real terminal.
    Those codes land *between* "FAILED" and the test id ("FAILED\x1b[0m
    tests/..."), which silently breaks `_FAILURE_LINE_RE`'s literal "FAILED "
    match while the passed/failed count regexes above keep matching fine (the
    numbers in the summary line aren't split by escape codes) -- so the bug
    only shows up as an empty `failures` list, not a crash. Forcing no-color
    makes the output identical no matter what's calling this function.
    """
    target = test_path or "tests"
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--color=no", target],
        cwd=repo_path,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    output = proc.stdout + proc.stderr
    failed = sum(int(m.group(1)) for m in _FAILED_COUNT_RE.finditer(output))
    passed = sum(int(m.group(1)) for m in _PASSED_COUNT_RE.finditer(output))
    failures = _FAILURE_LINE_RE.findall(output)
    return TestResult(passed=passed, failed=failed, total=passed + failed, failures=failures, raw_output=output)
