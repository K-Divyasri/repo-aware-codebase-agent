# Deploy checklist

A tight pass/fail list before you call this project "shipped". Two halves: first the
DONE-WHEN (does the thing actually work?), then the portfolio rules (can a recruiter
find it and trust it?). Tick every box.

## DONE-WHEN — the project does what it claims

- [ ] **Parses a real repo via AST, not prose chunking.** `python -m codeagent index`
      (or lab 01 / notebook 01) reports one chunk per function/method/class in
      `cartlogic`, each with a `kind`, a `lineno`, and its own docstring/code — not a
      fixed-size text window.
- [ ] **The call graph recovers context plain vector search misses.** Run lab 04 /
      notebook 05: searching "shipping cost calculation" with plain vector search
      alone should *not* put `calculate_shipping` first (a shorter wrapper property
      outranks it — a real, documented length-bias property of the embedder). Graph
      expansion (`search_with_graph_expansion`) should recover it via the caller/callee
      edges. Both halves of that story need to be true, not just the second half.
- [ ] **The agent fixes real, seeded bugs and proves it.** `python -m codeagent eval`
      (or lab 08 / notebook 10) reports `6/6 tasks passed` — five fix tasks (one per
      seeded bug in `data/target_repo`) plus one explain task, each scored against a
      **fresh sandbox** so no task's fix leaks into another's run.
- [ ] **Sandboxing actually protects the original repo.** Run any fix task, then check
      `data/target_repo/cartlogic/shipping.py` on disk still has the original bug —
      the agent only ever edits a disposable `tempfile.mkdtemp()` copy.
- [ ] **The offline/real split is real, not cosmetic.** `codeagent fix --real` (with
      `ANTHROPIC_API_KEY` set) drives the same five tools through an actual Claude
      tool-use loop instead of the `KNOWN_FIXES` lookup table — check
      `result.tool_trace` shows a different, model-chosen sequence of calls, not the
      same fixed three-step dance every time.

## Portfolio rules — the repo lands with a recruiter

- [ ] **Root `README.md` covers problem / skills / run steps / results.** Someone who
      knows nothing about the project understands it in twenty seconds and can run it.
- [ ] **A screenshot or short GIF of the Streamlit demo is embedded.** A repo that's
      all text reads as unfinished.
- [ ] **A live URL is in the README.** The Streamlit demo, offline, free, keyless. A
      clickable demo is what makes this land.
- [ ] **Secrets are never committed.** `git ls-files | Select-String ".env"` shows only
      `build_from_scratch/.env.example` -- never a bare `.env`. `ANTHROPIC_API_KEY`
      lives in the host's secrets vault, not the repo.
- [ ] **CI is green.** `.github/workflows/ci.yml` runs `pytest -q` (42 tests) on every
      push and passes on a clean machine. All tests are offline, so CI is keyless.
- [ ] **The public demo defaults to offline.** The "use real Claude" checkbox starts
      unticked and the app warns instead of erroring if no key is set — so the live
      demo can't spend your credits just from people clicking around.
- [ ] **The repo is pinned on your GitHub profile.** First thing a recruiter sees.
