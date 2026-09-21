# repo-aware-codebase-agent

A repo-aware agent for `cartlogic`, a tiny toy shopping-cart pricing library
checked into `data/target_repo`. It parses the repo's AST into symbols and a
call graph, indexes them for search, runs the test suite in a disposable
sandbox copy, and proposes diffs to fix the 5 bugs seeded in that repo.

Everything runs fully offline by default, with no API key. An optional flag
switches the agent to a genuine Claude tool-use loop.

## How it works

- **Parsing** (`codeagent/parsing.py`): Python's stdlib `ast` module turns every
  function, method and class into a symbol with its exact source text.
- **Call graph** (`codeagent/graph.py`): a static graph of which symbol calls
  which, built by name matching over `ast.Call` nodes. It does not resolve
  types, so it is a deliberate simplification suited to a small single-language
  repo.
- **Index and search** (`codeagent/chunking.py`, `embedding.py`, `index.py`):
  one chunk per symbol, embedded with a from-scratch hashing vectorizer (numpy
  only, no model download) whose tokenizer splits snake_case and camelCase.
  Search returns vector hits and then expands them across the call graph with
  direct callers and callees.
- **Sandbox** (`codeagent/sandbox.py`, `diffing.py`): every run works on a
  throwaway copy of `data/target_repo`, never the original. Proposed fixes come
  back as unified diffs.
- **Tools** (`codeagent/tools.py`): `list_files`, `read_file`, `search_code`,
  `run_tests` and `propose_fix`, with Anthropic tool-use schemas.
- **Agent** (`codeagent/agent.py`): offline mode is a deterministic lookup, not
  reasoning. It runs the tests, picks the failing test the task text is about,
  and applies the matching entry from a hand-written table of fixes for the 5
  seeded bugs. Asked about anything else, it falls back to search-and-explain
  rather than inventing a fix. Real mode (`--real`) runs a Claude tool-use loop
  over the same tools.
- **Eval** (`codeagent/eval.py`): 6 tasks (5 fixes, 1 explain question), each in
  its own fresh sandbox, with a pass/fail scorecard.

## Setup

```
pip install -r requirements.txt
# or: pip install -e .
```

The core needs only numpy. Streamlit (for the web demo) and pytest are also in
`requirements.txt`. The Anthropic SDK, sentence-transformers and tree-sitter are
optional and commented out there.

## Try it

```
python -m codeagent index
python -m codeagent search "shipping cost"
python -m codeagent tests
python -m codeagent fix "the shipping tests are failing"
python -m codeagent ask "where is tax calculated?"
python -m codeagent eval
```

`eval` runs the 6-task scorecard and prints which tasks passed.

## Tests

```
python -m pytest -q
```

The suite runs offline and needs no API key.

## Web demo

```
streamlit run app.py
```

A chat-style UI: type a task, run the agent, and see the tool-call trace, the
proposed diff, and the before/after test counts.

## Real Claude mode

Pass `--real` to `fix`, `ask` or `eval` for a genuine Claude tool-use loop. It
needs `ANTHROPIC_API_KEY` and the optional extra:

```
pip install -e .[llm]
```

Copy `.env.example` to `.env` to set the key and, optionally, `CODEAGENT_MODEL`.

## Layout

```
codeagent/            the package (parsing, graph, index, sandbox, tools, agent, eval)
tests/                offline pytest suite
data/target_repo/     the cartlogic toy repo with 5 seeded bugs
generate_target_repo.py   regenerates data/target_repo
app.py                Streamlit demo
hosting/              deployment guide, checklist and a CI workflow template
```
