# Publishing the Repo-Aware Codebase Agent

Three things you can put online, cheapest and easiest first:

1. **The code on GitHub** — a clean repo with a README and green CI. Do this one no
   matter what.
2. **The Streamlit demo** (`app.py`) on a free host - a clickable
   chat-style UI where you type a task ("the shipping tests are failing"), watch the
   agent's tool-call trace, and see the proposed diff. This is the link you paste in
   an interview.
3. **Real Claude tool use** (optional) — flip one checkbox in the hosted demo (or
   `--real` on the CLI) to swap the offline lookup-table planner for a genuine Claude
   agent loop.

The whole thing runs **fully offline by default** — Python's own `ast` module for
parsing, a from-scratch hashing embedder, a deterministic `KNOWN_FIXES` lookup table
for the "agent". No key, no account, no download. That's what makes it free to host:
a deployed demo works for anyone immediately and can't run up a bill, because nothing
calls a paid API unless you explicitly turn it on.

---

## The layout you're working with

```
repo-aware-codebase-agent/       <- this whole folder is your GitHub repo
├── app.py                       <- the Streamlit chat-style demo
├── codeagent/                   <- the package (parsing, graph, index, agent, ...)
├── requirements.txt
├── tests/                       <- 42 offline tests
├── .env.example                 <- safe to commit; the real .env is git-ignored
├── .gitignore
├── generate_target_repo.py      <- writes data/target_repo/ (not committed, see below)
├── hosting/                     <- you are here (this guide, deploy checklist, CI)
└── README.md                    <- the front page a recruiter opens
```

Two things follow from this:

- **GitHub gets the whole repo folder.** The CI workflow and
  the root README are written assuming the repo root is this folder.
- **The app *code* lives at the repo root.** When you point a host at it, the
  main file path is just `app.py`.
- **`data/target_repo/` is generated, not committed** (it's in `.gitignore`). It's the
  tiny toy `cartlogic` codebase the agent operates on — regenerated automatically the
  first time any test, lab, notebook, or the Streamlit app needs it, by calling
  `generate_target_repo.py`. Nothing to build or upload by hand.

---

## Step 0 — Get the code on GitHub

If you did an earlier project this is the same dance; skim it.

### Install Git and set your identity (once per machine)

Download from <https://git-scm.com/download/win>, run the installer clicking Next
through the defaults, open a **new** PowerShell window, and check:

```powershell
git --version
```

Then stamp your identity onto commits (use the email on your GitHub account):

```powershell
git config --global user.name "Your Name"
git config --global user.email "mathuransada@gmail.com"
```

### Know what must NOT go in the repo

The project ships one `.gitignore`, at the repo root (`.env`, `__pycache__/`,
`.pytest_cache/`, `.venv/`, notebook checkpoints). Open it and confirm it lists at least:

```
.env
data/target_repo/
__pycache__/
.pytest_cache/
.venv/
```

The one that matters most is **`.env`**. If you add an `ANTHROPIC_API_KEY`, it goes in
`.env`. A key is a password. Commit it once and it's on the public internet
**forever** — Git keeps the whole history, and bots scrape GitHub for leaked keys
within minutes of a push. Someone then runs up a bill on your account. So `.env`
**never** gets committed. The repo ships `.env.example` instead — variable names,
blank values — which is safe and *is* meant to be committed.

### Make the repo and push

Run these from the **project root** - the folder
with `codeagent/` and this `hosting/` folder inside it:

```powershell
cd repo-aware-codebase-agent
git init
git add .
git commit -m "Initial commit: repo-aware codebase agent (AST + call-graph retrieval, sandboxed fixes)"
```

Now the single most important check in this whole guide:

```powershell
git status
git ls-files | Select-String ".env"
```

The first should say `nothing to commit, working tree clean`. The second should show
`.env.example` and **nothing else**. If a bare `.env` shows up, you
staged a secret — jump to *Committed .env by accident* at the bottom before you push.

Then make an **empty** repo on github.com (the **+** menu, top-right → **New
repository**), name it `repo-aware-codebase-agent`, leave it **Public**, and do **not**
tick "Add a README / .gitignore / license" (an empty repo avoids a first-push
collision). Copy the URL it shows, then:

```powershell
git branch -M main
git remote add origin https://github.com/YOURNAME/repo-aware-codebase-agent.git
git push -u origin main
```

The first push opens a browser to sign in. If it asks for a *password* typed into the
terminal, that won't work — GitHub turned off password auth years ago. Use the browser
sign-in, or install the GitHub CLI (<https://cli.github.com>) and run `gh auth login`.

### Add CI so the tests run on every push

CI proves your tests pass on a clean machine, every push, and shows a green checkmark
recruiters notice. This `hosting/` folder ships a ready workflow at
`github_actions/ci.yml`. GitHub only runs workflows under `.github/workflows/`, so copy
it there. From the **project root**:

```powershell
mkdir .github\workflows
copy hosting\github_actions\ci.yml .github\workflows\ci.yml
git add .github\workflows\ci.yml
git commit -m "Add GitHub Actions CI to run the offline tests on every push"
git push
```

Open the repo's **Actions** tab to watch it: checkout → install Python 3.12 → install
`requirements.txt` → `pytest -q` (the
`ensure_target_repo` fixture in `conftest.py` regenerates `data/target_repo/` on the
runner automatically — nothing to commit or upload for that). It's **keyless** — every
test runs offline. Green means all 42 passed on GitHub's machine. If it goes red, click
the failed step and read the log bottom-up; a missing dependency is the usual cause.
Once green, grab the status badge (the workflow's Actions page → `...` menu → **Create
status badge**) and paste the markdown at the top of your root README.

---

## Step 1 — The Streamlit demo (the fastest public demo)

`app.py` is a small Streamlit chat-style interface over the exact
same `CodebaseAgent` the CLI uses — pick or type a task, hit **Run agent**, and see the
before/after test counts, the final message, the proposed diff, and the full tool-call
trace (expandable per call). It defaults to the offline planner, so a hosted demo is
free and keyless. This is the link worth having.

Two free hosts. **Streamlit Community Cloud** wires straight to the GitHub repo you
just pushed. **Hugging Face Spaces** also works and needs no card. Pick one.

### Path A — Streamlit Community Cloud

1. Go to <https://streamlit.io/cloud> and sign in with GitHub, granting read access to
   your repos.
2. **Create app** → **Deploy a public app from GitHub**.
3. **Repository:** `YOURNAME/repo-aware-codebase-agent`. **Branch:** `main`.
4. **Main file path:** the key field - point it at **`app.py`** (it sits at
   the repo root). Streamlit reads the
   `requirements.txt` sitting next to it at the repo root.
5. **Deploy.** The first launch calls `generate_target_repo.py` automatically (that's
   the guard at the top of `app.py`), then you have a public `*.streamlit.app` URL that
   works immediately, offline, for anyone.

If the build ever can't find dependencies, confirm `requirements.txt` sits at the
repo root next to `app.py`. Usually you won't need to.

Secrets on Streamlit Cloud live under the app's **⋮** menu → **Settings** → **Secrets**
(a small TOML editor). To let the hosted demo's "use real Claude" checkbox actually
work:

```toml
ANTHROPIC_API_KEY = "your-key-here"
```

Save; the app restarts and reads it from the environment. Leave it out and the demo
still runs fully, offline, with the checkbox falling back to offline mode (`app.py`
checks for the key and warns instead of erroring).

### Path B — Hugging Face Spaces (Streamlit SDK)

A "Space" is a free, always-on little web app. Docs:
<https://huggingface.co/docs/hub/en/spaces-sdks-streamlit>.

1. Make a free account at <https://huggingface.co>, then avatar → **New Space**.
2. **Space name:** `repo-aware-codebase-agent`. **Space SDK:** **Streamlit**. Free
   **CPU basic** hardware is plenty. **Create Space.**
3. A Space is its own Git repo and expects the app at its **root**. Our files already live at
   the repo root, so upload them to the Space root: `app.py`, the
   whole `codeagent/` folder, `generate_target_repo.py` (it goes right next to `app.py`,
   which is where the guard in `app.py` looks for it, or just pre-generate
   `data/target_repo/` locally and upload it too),
   and `requirements.txt`. Use the **Files** tab → **Add file** → **Upload files** and
   drag them in. Commit.
4. The Space builds (watch **Logs**), installs `requirements.txt`, launches Streamlit,
   and gives you a URL like
   `https://huggingface.co/spaces/YOURNAME/repo-aware-codebase-agent`.

Secrets on a Space: **Settings** → **Variables and secrets** → **New secret**. Add
`ANTHROPIC_API_KEY` there — stored encrypted, never in the repo or logs. The Space
restarts and picks it up from the environment.

> Streamlit Cloud is the easier of the two here specifically because it deploys your
> GitHub repo *as-is* - a Space is its own separate repo, so
> it needs the small copy-over above. If you only host one, make it Path A.

---

## Step 2 — Optional: real Claude tool use

By default, every task runs through the offline planner: run the tests, look up the one
known bug the failing test maps to, apply its exact fix, verify. That's honest about
being a lookup table, not reasoning — see `knowledge/01_why_this_project.md` and
`codeagent/agent.py`'s module docstring for why that's a deliberate,
zero-cost default rather than a limitation to hide.

Flip `real=True` (the "use real Claude" checkbox in the demo, or `--real` on the CLI)
and the exact same five tools — `list_files`, `read_file`, `search_code`, `run_tests`,
`propose_fix` — are driven by a genuine Claude tool-use loop against the plain
`anthropic` Python SDK instead. Get a key:

1. Go to <https://console.anthropic.com>, sign in, and create an API key.
2. Locally: paste it after `ANTHROPIC_API_KEY=` in `.env` (copy from `.env.example`
   first). On a host: put it in that host's secrets vault (Streamlit Secrets, Space
   secret) — **not** in the repo.

**Cost.** Every real-mode call is a billed API call (a handful of turns per task,
each a normal `messages.create` request) — see `knowledge/15_interview_prep.md` and
the Anthropic pricing page for current rates. This is a portfolio demo, not
high-traffic infra, so the cost of clicking around yourself is small; the risk is a
public demo where *anyone* can click the checkbox and rack up calls on your key.

So the rule for the deployed demo: **default to offline.** Leave the key unset on the
public app unless you specifically want visitors to be able to trigger real Claude
calls on your account. The offline planner is genuinely good enough to show the whole
pipeline — sandboxing, tool calls, diffing, test verification — working end to end;
real mode is the "and here's what changes with actual reasoning" upgrade, not the
baseline demo.

---

## Common Git mistakes (troubleshooting)

**Committed `.env` by accident.** Treat the key as compromised first — go to
<https://console.anthropic.com> and **revoke/rotate it**, because if you pushed, it's
already public. Then stop tracking the file:

```powershell
git rm --cached .env
git commit -m "Remove committed .env"
git push
```

`git rm --cached` only stops tracking it going forward — the key still sits in your Git
*history*, which is exactly why you rotate the key rather than trusting the delete.

**`error: failed to push` / push rejected.** The remote has commits your local repo
doesn't — almost always because you let GitHub add a README or license. Pull and
replay:

```powershell
git pull origin main --rebase
git push
```

Next time, create the repo completely empty.

**Authentication fails on push.** GitHub no longer accepts your account password in the
terminal. Install the GitHub CLI (<https://cli.github.com>) and run `gh auth login`,
following the browser prompts. It handles auth for all future Git commands.

**The hosted demo crashes on first load with a `data/target_repo` error.** It shouldn't
— `app.py` generates it automatically — but if you moved files around (e.g. the Hugging
Face Space reshuffle above) and broke the relative path from `app.py` to
`generate_target_repo.py`, that guard will fail. Check the host's logs for the exact
traceback; it'll point at the `subprocess.run` line in `app.py`.
