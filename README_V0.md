# Width-only Bayesian router: recommendation-only prototype (v0)

## Run
```
cd prototype && .venv/bin/streamlit run app.py
```
(`.venv` was created with `python3 -m venv .venv` and `pip install -r requirements.txt`. No API key is needed and
the app makes no network, LLM or API calls.)

Tests:
```
cd prototype && PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider -q tests
```

## What it does
Given a **DAG width** (1-5) and a **cost weight lambda** (0-300, quality points per USD per run), it recommends
one of single-agent (SA), workflow (WF) or multi-agent (MA), using the frozen width-only soft-count Beta model
that `router_dist.py` fitted on all 24 benchmark tasks (`data/bucket_model.json`, provenance in
`data/SOURCE.md`). For the chosen width it shows, per architecture: posterior mean quality ± SD, mean cost per run
(USD), utility `mu − lambda × cost`, and P(best) from 5,000 Monte Carlo draws with a fixed seed; plus the 95%
credible interval of U(recommended) − U(best alternative), a "no clear winner" flag (interval includes 0), a
"no evidence" flag for widths with no training data, and the number of categories and tasks behind the bucket.
Ties and empty buckets follow the router's rules: exact ties (< 1e-9) go to the lower cost, then SA, WF, MA; a
width with no data (3, 5) gets Beta(1,1) and the same fallback cost for all three, so it always shows SA as a
tie-break default with the "no evidence" flag.

## What it does NOT do
- It does not run SA, WF or MA, does not decompose a task, and does not compute a task's width: you enter it.
- It is not a validated router. In the benchmark's cross-validation the width-only router was not better than the
  best fixed strategy (see `results/router_dist/report.txt`). The prototype only reproduces its recommendation.
- Probabilities describe uncertainty in the 24-task benchmark evidence; they are not calibrated probabilities of
  success on other tasks. With one category behind a bucket (width 4) the cost SE is unavailable and cost is held
  fixed in the simulation, which can make P(best) look very confident (e.g. 1.000 at width 4, lambda 300).

## Status (details in VERIFIED.md)
- IMPLEMENTED: the app, the adapter (`router_adapter.py`), the tests.
- TESTED: `61 passed` (pytest, see VERIFIED.md): the adapter's recommendation, posterior means and SDs, P(best),
  95% interval, flags and default picks equal the original `router_dist.py` (run read-only in a subprocess) for
  widths 1, 2, 4 and empty width 3 at lambda 0, 10, 100, 300; the frozen model equals a fresh fit by
  `router_dist.py`; the hand-computed means and picks; the app renders and responds headlessly; a local server
  answered its health check.
- UNVERIFIED: see VERIFIED.md ("Not verified").

## Files
`app.py` (Streamlit UI), `router_adapter.py` (standalone copy of the router's recommendation formulas; ADAPTER
mode, see DECISIONS.md), `data/` (frozen model, evidence per width, provenance), `tools/make_evidence.py`,
`tests/`, `INSPECTION.md`, `DECISIONS.md`, `VERIFIED.md`, `SUMMARY.md`, `repo_state/` (git snapshots before/after).
