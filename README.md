# CRM agent-architecture recommender (research prototype)

A Streamlit prototype from a Master's AI capstone on **choosing between Single-Agent, Workflow and Multi-Agent LLM
architectures for CRM tasks**. You describe a CRM task; an LLM decomposes it into a subtask graph (DAG) using the
research decomposition prompt; you confirm the graph's width (how many subtasks can run in parallel); and a width-only
Bayesian router fitted on a 24-task benchmark recommends an architecture, with estimated quality, cost, utility and
uncertainty.

It **recommends only**: it never runs an architecture or connects to a CRM. In the project's evaluation the width-only
router did **not** outperform the best fixed architecture; the prototype demonstrates the selection mechanism and reports
its uncertainty honestly. Generated DAGs are LLM output and are not evaluated.

Main app: `app_v2.py`. (The `v1_*`/`v2_*` modules are part of this app, not old versions; earlier app versions are
kept only in the original capstone repository.)

## Run locally
Python 3.12.
```
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app_v2.py
```
Live decomposition needs an OpenAI API key, either exported in the shell (`export OPENAI_API_KEY=...`) or in
`.streamlit/secrets.toml` (copy `.streamlit/secrets.toml.example`; that file is git-ignored). Without a key the app still
works with the benchmark examples, the recorded generated examples and manual width.

## Deploy on Streamlit Community Cloud
1. Push this repo to GitHub (private is fine) and connect it at share.streamlit.io → **Create app**.
2. **Main file path:** `app_v2.py`. **Branch:** `clean-submission`.
3. **Advanced settings → Python version: 3.12** (numpy 2.0.1 has no wheels for newer Pythons).
4. **Advanced settings → Secrets:** paste, as a top-level key (no `[section]`, so it is also exposed as an
   environment variable, which is how the app reads it):
   ```
   OPENAI_API_KEY = "your-key-here"
   ```
5. Deploy. Dependencies come from `requirements.txt` at the repo root.

The app uses gpt-4o-mini; one decomposition costs roughly $0.0003.

## Data, licence and attribution
This repository contains task text and derived DAG decompositions from **CRMArena-Pro** (Huang et al., 2025;
Salesforce AI Research), which is released under **CC BY-NC 4.0** for research use. It uses a subset of 22 CRMArena-Pro
tasks plus 2 custom tasks, adds DAG decompositions of them, and is intended for **non-commercial academic use only**.
See `NOTICE.md`.

## Layout
`app_v2.py` (UI) · `live_decompose.py` (bridge to the research decomposer) · `research/decompose.py` (verbatim copy
of the research decomposer, pinned by sha256) · `router_adapter.py` (router) · `dag_width.py`, `v1_state.py`,
`v2_state.py`, `v2_recorded.py`, `v1_explain.py` · `data/` (frozen fitted model, example DAGs, recorded generations).
`data/SOURCE.md` records the provenance (and sha256) of the frozen model.

## Tests
The offline test suites (200 tests: 61 + 70 + 69, plus one opt-in live-API test that is skipped by default) live in
the original capstone repository, because they compare the prototype against research files not included here (the
decomposition cache, `router_dist.py` and earlier app versions). None of them needs an API key; the LLM is mocked.
