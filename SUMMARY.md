# SUMMARY: recommendation-only prototype (v0) of the width-only Bayesian router

## Priority tier reached
- Tier 1 (minimum): DONE and TESTED. The Streamlit app takes a DAG width (1-5) and lambda (0-300 slider plus quick
  buttons 0/10/100/300), loads the frozen model, computes U = mu − lambda × cost for SA, WF and MA, and recommends
  with the router's tie-break and empty-bucket behaviour.
- Tier 2 (uncertainty + tests): DONE and TESTED. SD, P(best) (5000 draws, fixed seed), 95% credible interval of the
  utility gap, "no clear winner" and "no evidence" flags; 61 tests.
- Tier 3 (polish): minimal only (warnings for flags, evidence section, captions). No further styling.

Mode: ADAPTER (`router_adapter.py`); reasons and the list of duplicated calculations in `DECISIONS.md`.

## Launch
```
cd prototype && .venv/bin/streamlit run app.py
```

## Tests
`PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider -v --color=no tests`
→ `61 passed in 1.00s` (full output: `test_output.txt`). Coverage: equality with the original `router_dist.py`
(run read-only in a subprocess) for widths 1, 2, 4 and empty width 3 at lambda 0, 10, 100, 300 (pick, tied set,
flags, means, SDs, costs, P(best), interval, no-clear-winner); frozen model = fresh router_dist fit; hand-computed
means and picks; empty widths 3 and 5; headless AppTest of the UI. A localhost server smoke test returned health
`ok` and HTTP 200 and was stopped.

## Mismatches
None. The hand-computed means (w1 0.1373/0.0989/0.1281, w2 0.3167/0.3250/0.4917, w4 0.5000/0.3333/0.3333) and the
expected picks (w1 SA, SA, MA, MA; w2 MA, MA, MA, SA; w4 SA throughout) all matched the code.

## Assumptions (see DECISIONS.md)
- Monte Carlo stream key 0 for the app (router_dist uses the task id), so app P(best) values are not the per-task
  values in `results/router_dist/report.txt` (D2).
- P(best) for the two non-recommended architectures is an addition computed from the same draws (D3).
- Empty-bucket cost = the all-24 model's stored `c_bar` (D4).
- Task counts per width frozen from the decomposition cache (D5). numpy pinned to 2.0.1 (D6).

## Unverified
- Visual appearance in a real browser; P(best) of the non-recommended architectures against the original;
  lambda values off the tested grid other than through the same code path; the evidence task lists against any
  source other than the decomposition cache; any claim about real-world performance (the router was not better
  than the best fixed strategy in the benchmark's cross-validation; this prototype only reproduces its
  recommendation). Full list in `VERIFIED.md`.

## File classification
(a) Pre-existing files that are in both snapshots: none of the user's untracked files. `report9.txt` and
`review_900002.md` were already COMMITTED on branch `prototype` (commit `4ee3f05`) before this work, so they
appear in neither snapshot as untracked. All ignored entries listed in `before.txt` (e.g. `.env`, existing
`__pycache__/` folders, `venv/`, `results/`) are identical in `after.txt` (set comparison: 0 entries only in
`before.txt`).

(b) New files, all under `prototype/` (untracked; plus `prototype/.venv/`, 10,046 ignored entries via
`prototype/.gitignore`):
`.gitignore, app.py, router_adapter.py, requirements.txt, README.md, INSPECTION.md, DECISIONS.md, VERIFIED.md,
SUMMARY.md, test_output.txt, data/bucket_model.json, data/SOURCE.md, data/bucket_evidence.json,
tools/make_evidence.py, tests/test_matches_router.py, tests/test_app.py, repo_state/before.txt,
repo_state/after.txt`.

(c) Changes outside `prototype/`: **NONE.** `git diff --name-only` and `git diff --cached --name-only` are empty in
both snapshots; the set difference after − before contains 0 entries outside `prototype/`; no new `__pycache__`
outside `prototype/` (checked with `find -newer`). `diff before.txt after.txt` exits 1 only because of the new
`prototype/` entries. Branch unchanged (`prototype`); nothing committed or pushed. Outside the repo,
`~/.streamlit/` pre-existed (2025-06-11) and was not changed.
