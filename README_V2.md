# CRM architecture recommender — v2 (automatic DAG decomposition)

## Launch
```
cd prototype && .venv_v2/bin/streamlit run app_v2.py
```
For live decomposition, `OPENAI_API_KEY` must be set in the shell that starts Streamlit (the app never reads `.env`).
Without a key, everything except "Generate DAG" works: benchmark examples, recorded generated examples, manual width.
v0 (`.venv/bin/streamlit run app.py`) and v1 (`.venv/bin/streamlit run app_v1.py`) are unchanged.

## Tests
```
cd prototype
PYTHONDONTWRITEBYTECODE=1 .venv_v2/bin/python -m pytest -p no:cacheprovider -q tests_v2      # v2 (LLM mocked)
RUN_LIVE_DECOMP=1 PYTHONDONTWRITEBYTECODE=1 .venv_v2/bin/python -m pytest -p no:cacheprovider -q -s tests_v2/test_v2_live.py  # one real call; needs a key
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider -q tests            # v0
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider -q tests_v1         # v1
```

## What it does
**CRM task (+ optional context) → LLM decomposition → validated DAG width → your confirmation → Bayesian router →
recommendation.**
1. **Describe the task.** Type a CRM request (and optional context), or pick a benchmark example, an illustrative
   example or a recorded generated example.
2. **Task structure.** "Generate DAG with LLM" sends the task to the research decomposition prompt (gpt-4o-mini,
   temperature 0, the research validation and retry logic, reused unchanged from `decomposition/decompose.py`). The app
   shows the subtasks, their dependencies and the width (computed twice, by the research code and the prototype; both
   must agree). You then **confirm** the width, **regenerate** (the app warns if the width changes), or **correct** it.
3. **Recommendation.** With a cost preference (lambda 0-300), the unchanged width-only Bayesian router recommends
   Single-Agent, Workflow or Multi-Agent, with estimated quality ± SD, cost, utility, chance of being best, a 95%
   interval, a plain-English explanation and warnings for no evidence, no clear winner and limited evidence.

## What it does NOT do
- It does not execute any architecture or connect to a CRM. It only recommends.
- A generated DAG is **not evaluated**: the two width calculations agreeing means the width is computed consistently
  for that DAG, not that the decomposition is correct. Check the subtasks before trusting the width.
- It does not improve the router: in the project's evaluation the width-only router did not outperform the best fixed
  strategy. v2 changes how the width is obtained, not how good the recommendation is.

## Kinds of examples
- **Benchmark example — in sample**: stored research DAGs of tasks the router was fitted on.
- **Illustrative example**: hand-written DAG, not evidence.
- **Recorded LLM-generated example — not evaluated**: four new CRM queries decomposed once with the live path and stored,
  so the demo works without network or key. Not benchmark tasks.

## Consistency with the research
- Prompt, model, temperature, validation and retries are the research code, imported (not copied) and pinned by sha256
  (`decompose.py` @ `1e7e83b`); if that file changes, live decomposition is disabled.
- With no context, the decomposer receives exactly the task text, as in the research. With context, the text is
  appended under a fixed header and the result is flagged "context included" (a difference from the research setting).
- Custom tasks have no benchmark category, so the research code's category-based privacy refusal check is not added.
- Generated DAGs live only in the Streamlit session; nothing is written to the research cache or anywhere else.

## Demo script (≈2 minutes)
1. Pick **"Retention note for complaining customers with a renewal due" [Recorded LLM-generated]**: two independent
   retrievals → width 2. Click **Use generated width (2)**, then **Get recommendation** → Multi-Agent, "no clear winner".
2. Click **lambda = 300** → Single-Agent; the explanation says Multi-Agent's quality is higher but Single-Agent's cost wins.
3. Pick **"Qualify a new inbound lead"** (width 4) → shows the limited-evidence warning.
4. Live (only if a key is set and the network is reliable): choose **Custom task**, type a request, click **Generate DAG
   with LLM**, inspect the subtasks, confirm, recommend. Click **Regenerate** to show the stability check.

## Known limitations
- Most CRM requests decompose to width 1, where the recommendation is the same for every task (SA at low lambda, MA at
  100-300). Widths 2 and 4 rest on two and one benchmark categories; 3 and 5+ have no evidence.
- LLM output can vary even at temperature 0; use Regenerate to see whether the width is stable.
- Live calls need network and a key; each takes a few seconds (up to 3 attempts) and costs about $0.0003.
- Attempt and cost counters are shared within the Streamlit process (fine for one user; see DECISIONS_V2 D12).
- Visual appearance was not checked in a real browser.
