"""A small chat-style demo of the codebase agent, built with Streamlit.

    streamlit run app.py

Type a task -- "the shipping tests are failing" or "where is tax calculated?"
-- hit Run agent, and see the tool-call trace, the proposed diff, and the
before/after test counts. Offline by default, so this demos with no API key;
tick "use real Claude" only if ANTHROPIC_API_KEY is set.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import streamlit as st

_HERE = Path(__file__).resolve()
_ROOT = _HERE.parent  # project root
_TARGET_REPO = _ROOT / "data" / "target_repo"
if not (_TARGET_REPO / "cartlogic").exists():
    # If data/target_repo is missing (e.g. deleted), regenerate it once.
    subprocess.run([sys.executable, "generate_target_repo.py"], cwd=_ROOT, check=True)

from codeagent.agent import CodebaseAgent
from codeagent.sandbox import Sandbox

st.set_page_config(page_title="Repo-Aware Codebase Agent", page_icon="\U0001f6e0️")
st.title("Repo-Aware Codebase Agent")
st.caption(
    "An agent that parses cartlogic (a tiny shopping-cart pricing library) via its AST and "
    "call graph, then reads, searches, tests, and proposes fixes for real seeded bugs."
)

use_real = st.sidebar.checkbox("Use real Claude (needs ANTHROPIC_API_KEY)", value=False)
if use_real and not os.environ.get("ANTHROPIC_API_KEY"):
    st.sidebar.warning("No ANTHROPIC_API_KEY found - running offline instead.")
    use_real = False

examples = [
    "The shipping tests are failing, please fix it.",
    "The tax tests are failing, please fix it.",
    "The bulk discount tests are failing, please fix it.",
    "The cart total tests are failing, please fix it.",
    "The loyalty points tests are failing, please fix it.",
    "Where is shipping cost calculated and what does it depend on?",
]
choice = st.selectbox("Pick an example, or type your own", [""] + examples)
task = st.text_area("Task", value=choice, placeholder="Describe a bug to fix, or ask where something is...")

if st.button("Run agent", type="primary") and task.strip():
    with st.spinner("Working..."):
        with Sandbox() as sandbox:
            agent = CodebaseAgent(sandbox)
            result = agent.run(task, real=use_real)

    col1, col2, col3 = st.columns(3)
    col1.metric("Success", "yes" if result.success else "no")
    if result.tests_before:
        col2.metric("Tests before", f"{result.tests_before.passed}/{result.tests_before.total}")
    if result.tests_after:
        col3.metric("Tests after", f"{result.tests_after.passed}/{result.tests_after.total}")

    st.subheader("Final message")
    st.write(result.final_message)

    if result.diff:
        st.subheader("Proposed diff")
        st.code(result.diff, language="diff")

    st.subheader("Tool-call trace")
    if not result.tool_trace:
        st.write("(no tool calls)")
    for i, step in enumerate(result.tool_trace, start=1):
        with st.expander(f"{i}. {step['tool']}({step['input']})"):
            st.json(step["result"])
