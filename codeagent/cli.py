"""Command-line interface to the codebase agent.

Subcommands:

    python -m codeagent index                     parse the repo, print a symbol/index summary
    python -m codeagent search "shipping cost"     semantic + graph search over the repo
    python -m codeagent tests [--path P]           run the target repo's test suite
    python -m codeagent fix "task" [--real]        have the agent fix a failing test
    python -m codeagent ask "task" [--real]        have the agent answer/locate something
    python -m codeagent eval [--real]              run the eval scorecard

Every command works in a fresh Sandbox copy of data/target_repo, and is fully
offline by default -- `--real` needs ANTHROPIC_API_KEY and the `anthropic`
package (`pip install -e .[llm]`).
"""

from __future__ import annotations

import argparse

from .agent import CodebaseAgent
from .chunking import build_chunks
from .embedding import make_embedder
from .eval import run_eval
from .graph import CallGraph
from .index import SymbolIndex
from .parsing import Symbol, parse_repo
from .sandbox import Sandbox
from .sandbox import run_tests as sandbox_run_tests


def _build_index(repo_path) -> tuple[list[Symbol], CallGraph, SymbolIndex]:
    symbols = parse_repo(repo_path)
    graph = CallGraph(symbols)
    chunks = build_chunks(symbols, graph)
    index = SymbolIndex.build(chunks, make_embedder("hashing"))
    return symbols, graph, index


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="codeagent", description="A repo-aware agent for the cartlogic toy codebase."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("index", help="parse the target repo and print a symbol/index summary")

    p_search = sub.add_parser("search", help="semantic + graph search over the repo")
    p_search.add_argument("query")
    p_search.add_argument("-k", type=int, default=5, help="number of top vector hits (default 5)")

    p_tests = sub.add_parser("tests", help="run the target repo's test suite")
    p_tests.add_argument("--path", default=None, help="specific test file or path")

    p_fix = sub.add_parser("fix", help="have the agent fix a failing test")
    p_fix.add_argument("task")
    p_fix.add_argument("--real", action="store_true", help="use a real Claude tool-use loop")
    p_fix.add_argument("--model", default=None)

    p_ask = sub.add_parser("ask", help="have the agent answer or locate something")
    p_ask.add_argument("task")
    p_ask.add_argument("--real", action="store_true", help="use a real Claude tool-use loop")
    p_ask.add_argument("--model", default=None)

    p_eval = sub.add_parser("eval", help="run the eval scorecard")
    p_eval.add_argument("--real", action="store_true", help="use a real Claude tool-use loop")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "index":
        with Sandbox() as sandbox:
            symbols, graph, index = _build_index(sandbox.path)
            source = sandbox.source
        print(f"Parsed {len(symbols)} symbols from {source}")
        by_kind: dict[str, int] = {}
        for s in symbols:
            by_kind[s.kind] = by_kind.get(s.kind, 0) + 1
        for kind, n in sorted(by_kind.items()):
            print(f"  {kind}: {n}")
        print(f"Indexed {len(index.chunks)} chunks.")
        return 0

    if args.command == "search":
        with Sandbox() as sandbox:
            _, graph, index = _build_index(sandbox.path)
            hits = index.search_with_graph_expansion(args.query, k=args.k, graph=graph)
            if not hits:
                print("No results.")
                return 0
            for h in hits:
                print(f"[{h.via}] {h.chunk.symbol_name}  ({h.chunk.file}:{h.chunk.lineno})  score={h.score:.3f}")
                if h.chunk.callers:
                    print(f"    called by: {', '.join(h.chunk.callers)}")
                if h.chunk.callees:
                    print(f"    calls: {', '.join(h.chunk.callees)}")
        return 0

    if args.command == "tests":
        with Sandbox() as sandbox:
            result = sandbox_run_tests(sandbox.path, test_path=args.path)
        print(result.raw_output)
        print(f"{result.passed}/{result.total} passing")
        return 0 if result.failed == 0 else 1

    if args.command in ("fix", "ask"):
        with Sandbox() as sandbox:
            agent = CodebaseAgent(sandbox)
            result = agent.run(args.task, real=args.real, model=args.model)
        print(result.final_message)
        if result.diff:
            print("\n--- diff ---")
            print(result.diff)
        if result.tests_before and result.tests_after:
            print(f"\ntests before: {result.tests_before.passed}/{result.tests_before.total} passing")
            print(f"tests after:  {result.tests_after.passed}/{result.tests_after.total} passing")
        print(f"\nsuccess: {result.success}")
        return 0 if result.success else 1

    if args.command == "eval":
        report = run_eval(real=args.real)
        print(report.table())
        return 0 if report.n_passed == len(report.reports) else 1

    return 1
