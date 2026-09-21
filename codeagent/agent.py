"""The agent: offline by default, a real Claude tool-use loop when asked.

OFFLINE (`real=False`, the default, no API key needed) does not "reason" about
the bug at all. It's a small deterministic lookup: run the tests, take the
first failing test that the task text seems to be about, and look it up in
`KNOWN_FIXES` -- a hand-written table mapping each of the 5 bugs this project
seeds into `data/target_repo` to its exact one-line fix. That's an honest
stand-in for real reasoning, the same pattern as the other offline defaults
here (a hashing embedder instead of a neural one): it lets the whole pipeline -- sandboxing, tool
calls, diffing, test verification -- run and be tested with zero cost and no
network. It is NOT a general bug-fixer. Ask it about a bug that isn't one of
the 5 seeded ones and it has nothing to look up; it falls back to a search-
and-explain response instead of inventing a fix.

REAL (`real=True`, needs `ANTHROPIC_API_KEY`) is a genuine tool-use loop
against the plain `anthropic` Python SDK -- not LiteLLM, not a separate
"Claude Agent SDK" package. A tool-use loop (send messages + tool schemas,
read back `tool_use` blocks, run the tools, feed `tool_result` blocks back in,
repeat) is inherently provider-specific: the message and content-block shapes
Anthropic expects are not the shapes OpenAI or Gemini expect. So rather than
hide that behind an abstraction, this project builds the real thing directly
against `anthropic.Anthropic().messages.create(model=..., tools=TOOL_SCHEMAS,
messages=...)`, looping until the model returns a turn with no tool calls, or
`max_turns` is hit.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from .chunking import build_chunks
from .embedding import make_embedder
from .graph import CallGraph
from .index import SymbolIndex
from .parsing import parse_repo
from .sandbox import Sandbox, TestResult
from .sandbox import run_tests as _sandbox_run_tests
from .tools import TOOL_SCHEMAS, ToolRunner

DEFAULT_MODEL = os.environ.get("CODEAGENT_MODEL", "claude-sonnet-5")

_SYSTEM_PROMPT = (
    "You are a repo-aware coding agent working on a small Python package called cartlogic. "
    "You have tools to list files, read files, search the code (semantic + call-graph), run "
    "the test suite, and propose a fix by writing a file's full new contents. When asked to "
    "fix a failing test: run the tests, read the relevant file, make the smallest correct "
    "change, propose the fix, then re-run the tests to confirm they pass. When asked where "
    "something is or how it works: search the code and answer directly, naming the file and "
    "any callers/callees you found. Once you have a final answer, respond with plain text and "
    "no further tool calls."
)

# The 5 bugs this project seeds into data/target_repo, keyed by the pytest test id that
# catches each one. This is a deterministic stand-in for reasoning -- see the module
# docstring -- not a general bug-fixing strategy.
KNOWN_FIXES: dict[str, dict[str, str]] = {
    "tests/test_shipping.py::test_free_shipping_at_exactly_threshold": {
        "file": "cartlogic/shipping.py",
        "old": "    if subtotal > FREE_SHIPPING_THRESHOLD:  # BUG: should be >=, so exactly $50.00 wrongly gets charged",
        "new": "    if subtotal >= FREE_SHIPPING_THRESHOLD:",
    },
    "tests/test_tax.py::test_calculate_tax_rounds_correctly": {
        "file": "cartlogic/tax.py",
        "old": "    return int(amount * rate * 100) / 100",
        "new": "    return round(amount * rate, 2)",
    },
    "tests/test_discounts.py::test_apply_bulk_discount_at_exactly_ten": {
        "file": "cartlogic/discounts.py",
        "old": "    if quantity > BULK_DISCOUNT_QUANTITY:  # BUG: should be >=, so exactly 10 items get no discount",
        "new": "    if quantity >= BULK_DISCOUNT_QUANTITY:",
    },
    "tests/test_cart.py::test_total_applies_discount": {
        "file": "cartlogic/cart.py",
        "old": "        return round(self.subtotal + self.shipping + self.tax, 2)",
        "new": "        return round(self.subtotal - self.discount + self.shipping + self.tax, 2)",
    },
    "tests/test_loyalty.py::test_loyalty_points_rounds_correctly": {
        "file": "cartlogic/loyalty.py",
        "old": "    return int(total // 1)",
        "new": "    return round(total)",
    },
}

# Words that signal "this task wants a bug fixed" rather than "explain/locate something".
_FIX_KEYWORDS = ("fix", "failing", "fails", "bug", "broken", "wrong", "incorrect")


def _looks_like_fix_task(task: str) -> bool:
    task_lower = task.lower()
    return any(kw in task_lower for kw in _FIX_KEYWORDS)


def _pick_target_test(task: str, failures: list[str]) -> str | None:
    """Which failing test the task text seems to be about, else the first failure."""
    task_lower = task.lower()
    for test_id in failures:
        module = test_id.split("::")[0]
        stem = Path(module).stem
        if stem.startswith("test_"):
            stem = stem[len("test_") :]
        if stem and (stem in task_lower or stem.rstrip("s") in task_lower):
            return test_id
    return failures[0] if failures else None


def _render_explain_message(task: str, hits: list[dict]) -> str:
    """A templated final message naming the top matching symbol(s), their file, and neighbors.

    The top vector hit is often a thin wrapper (a one-line property or method
    that just delegates), not the symbol that actually does the work -- that's
    why `search_code` graph-expands with callers/callees in the first place.
    So this doesn't only describe hits[0]; it looks up each caller/callee's own
    file from the (already-retrieved) hit list and names it too, e.g. "Calls:
    calculate_shipping (cartlogic/shipping.py)" instead of a bare symbol name.
    """
    if not hits:
        return f"No matching symbols found for: {task!r}"
    by_name = {h["symbol"]: h for h in hits}

    def _describe(names: list[str]) -> str:
        parts = []
        for name in names:
            other = by_name.get(name)
            parts.append(f"{name} ({other['file']})" if other else name)
        return ", ".join(parts)

    top = hits[0]
    lines = [
        f"Top match: `{top['symbol']}` ({top['kind']}) in {top['file']}, line {top['lineno']}.",
        f'Docs/code: "{top["snippet"]}"',
    ]
    lines.append(f"Called by: {_describe(top['callers'])}." if top["callers"] else "Called by: nothing else in the repo.")
    lines.append(f"Calls: {_describe(top['callees'])}." if top["callees"] else "Calls: nothing else in the repo.")
    # "What does it depend on" means the reader wants the callee's own logic, not just its
    # name and file -- so pull in a snippet of the first callee we actually retrieved a chunk for.
    for callee_name in top["callees"]:
        callee = by_name.get(callee_name)
        if callee:
            lines.append(f'`{callee_name}` does: "{callee["snippet"]}"')
            break
    others = [h["symbol"] for h in hits[1:4]]
    if others:
        lines.append(f"Other related symbols: {_describe(others)}.")
    return " ".join(lines)


def _to_test_result(d: dict) -> TestResult:
    return TestResult(passed=d["passed"], failed=d["failed"], total=d["total"], failures=d["failures"])


@dataclass
class AgentResult:
    """The outcome of one `CodebaseAgent.run()` call."""

    final_message: str
    tool_trace: list[dict] = field(default_factory=list)
    diff: str | None = None
    tests_before: TestResult | None = None
    tests_after: TestResult | None = None
    success: bool = False


class CodebaseAgent:
    """Ties a Sandbox to a SymbolIndex + CallGraph and runs offline or real tasks against it."""

    def __init__(
        self,
        sandbox: Sandbox,
        index: SymbolIndex | None = None,
        graph: CallGraph | None = None,
        embedder=None,
    ) -> None:
        self.sandbox = sandbox
        if graph is None:
            symbols = parse_repo(sandbox.path)
            graph = CallGraph(symbols)
            if index is None:
                chunks = build_chunks(symbols, graph)
                index = SymbolIndex.build(chunks, embedder or make_embedder("hashing"))
        elif index is None:
            # A graph was given but no index -- rebuild chunks/index from the same symbols.
            symbols = parse_repo(sandbox.path)
            chunks = build_chunks(symbols, graph)
            index = SymbolIndex.build(chunks, embedder or make_embedder("hashing"))
        self.graph = graph
        self.index = index
        self.runner = ToolRunner(sandbox, index, graph)

    def _test_result(self) -> TestResult:
        """A baseline test run, outside the tool trace (bookkeeping, not a planning step)."""
        return _sandbox_run_tests(self.sandbox.path)

    def _call_tool(self, name: str, tool_input: dict, trace: list[dict]) -> dict:
        result = self.runner.dispatch(name, tool_input)
        trace.append({"tool": name, "input": tool_input, "result": result})
        return result

    def run(self, task: str, *, real: bool = False, model: str | None = None, max_turns: int = 8) -> AgentResult:
        """Run one task against this agent's sandbox: fix a known bug, or explain/locate something."""
        tests_before = self._test_result()
        trace: list[dict] = []
        if real:
            final_message, diff, success, tests_after = self._run_real(
                task, trace, model=model, max_turns=max_turns
            )
        else:
            final_message, diff, success, tests_after = self._run_offline(task, tests_before, trace)
        return AgentResult(
            final_message=final_message,
            tool_trace=trace,
            diff=diff,
            tests_before=tests_before,
            tests_after=tests_after,
            success=success,
        )

    # ------------------------------------------------------------------ #
    # Offline: deterministic KNOWN_FIXES lookup, or a search-and-explain fallback.
    # ------------------------------------------------------------------ #

    def _run_offline(
        self, task: str, tests_before: TestResult, trace: list[dict]
    ) -> tuple[str, str | None, bool, TestResult]:
        if _looks_like_fix_task(task) and tests_before.failures:
            target_id = _pick_target_test(task, tests_before.failures)
            fix = KNOWN_FIXES.get(target_id) if target_id else None
            if fix is not None:
                self._call_tool("read_file", {"path": fix["file"]}, trace)
                raw_text = (self.sandbox.path / fix["file"]).read_text(encoding="utf-8")
                if fix["old"] not in raw_text:
                    message = (
                        f"Found failing test `{target_id}`, but the expected buggy line was "
                        f"not present in {fix['file']} -- no changes made."
                    )
                    return message, None, False, tests_before
                new_text = raw_text.replace(fix["old"], fix["new"])
                fix_result = self._call_tool(
                    "propose_fix", {"file": fix["file"], "new_content": new_text}, trace
                )
                after_dict = self._call_tool("run_tests", {}, trace)
                after = _to_test_result(after_dict)
                success = target_id not in after.failures
                message = (
                    f"Found failing test `{target_id}`. Applied the known fix to {fix['file']} "
                    f"(changed to `{fix['new'].strip()}`). Tests now: {after.passed}/{after.total} passing."
                )
                return message, fix_result["diff"], success, after

        # Fallback: this isn't (or doesn't match) a known fix -- search and explain instead.
        hits = self._call_tool("search_code", {"query": task, "k": 5}, trace)["hits"]
        return _render_explain_message(task, hits), None, bool(hits), tests_before

    # ------------------------------------------------------------------ #
    # Real: a genuine Claude tool-use loop via the plain anthropic SDK.
    # ------------------------------------------------------------------ #

    def _run_real(
        self, task: str, trace: list[dict], *, model: str | None, max_turns: int
    ) -> tuple[str, str | None, bool, TestResult]:
        import anthropic  # noqa: PLC0415 (lazy: only needed for --real)

        client = anthropic.Anthropic()
        model = model or DEFAULT_MODEL
        messages: list[dict] = [{"role": "user", "content": task}]
        diff: str | None = None

        for _ in range(max_turns):
            response = client.messages.create(
                model=model,
                max_tokens=1024,
                system=_SYSTEM_PROMPT,
                tools=TOOL_SCHEMAS,
                messages=messages,
            )
            tool_uses = [block for block in response.content if block.type == "tool_use"]

            if not tool_uses:
                text = "".join(block.text for block in response.content if block.type == "text")
                after = self._test_result()
                success = after.total > 0 and after.failed == 0 if diff else True
                return text, diff, success, after

            messages.append({"role": "assistant", "content": response.content})
            tool_results = []
            for block in tool_uses:
                result = self.runner.dispatch(block.name, block.input)
                trace.append({"tool": block.name, "input": block.input, "result": result})
                if block.name == "propose_fix" and "diff" in result:
                    diff = result["diff"]
                tool_results.append(
                    {"type": "tool_result", "tool_use_id": block.id, "content": json.dumps(result)}
                )
            messages.append({"role": "user", "content": tool_results})

        after = self._test_result()
        return "Stopped after reaching max_turns without a final answer.", diff, False, after
