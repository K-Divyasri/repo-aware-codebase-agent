# codeagent -- build from scratch

A repo-aware agent for `cartlogic`, a tiny toy shopping-cart pricing library
checked into `../data/target_repo`. It parses the repo's AST into symbols and
a call graph, indexes them for search, runs the test suite in a disposable
sandbox copy, and proposes diffs to fix the 5 bugs seeded in that repo.

## Setup

```
pip install -r requirements.txt
# or: pip install -e .
```

## Try it

```
python -m codeagent index
python -m codeagent search "shipping cost"
python -m codeagent tests
python -m codeagent fix "the shipping tests are failing"
python -m codeagent ask "where is tax calculated?"
python -m codeagent eval
```

## Tests

```
python -m pytest -q
```

## Web demo

```
streamlit run app.py
```

Everything above runs fully offline, no API key needed. Pass `--real` to
`fix`/`ask`/`eval` for a genuine Claude tool-use loop (needs `ANTHROPIC_API_KEY`
and `pip install -e .[llm]`).
