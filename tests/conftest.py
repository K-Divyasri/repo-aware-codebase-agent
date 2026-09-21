"""Shared fixtures. Everything here is offline: stdlib ast parsing, hashing embedder."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from codeagent.chunking import build_chunks
from codeagent.embedding import make_embedder
from codeagent.graph import CallGraph
from codeagent.index import SymbolIndex
from codeagent.parsing import parse_repo

ROOT = Path(__file__).resolve().parents[1]
TARGET_REPO = ROOT / "data" / "target_repo"


@pytest.fixture(scope="session", autouse=True)
def ensure_target_repo() -> None:
    """Regenerate data/target_repo before any test runs, so a fresh checkout just works."""
    if not (TARGET_REPO / "cartlogic").exists():
        subprocess.run([sys.executable, "generate_target_repo.py"], cwd=ROOT, check=True)


@pytest.fixture(scope="session")
def repo_symbols(ensure_target_repo):
    """Every Symbol parsed out of data/target_repo, built once for the whole session."""
    return parse_repo(TARGET_REPO)


@pytest.fixture(scope="session")
def call_graph(repo_symbols):
    return CallGraph(repo_symbols)


@pytest.fixture(scope="session")
def symbol_index(repo_symbols, call_graph):
    chunks = build_chunks(repo_symbols, call_graph)
    return SymbolIndex.build(chunks, make_embedder("hashing"))
