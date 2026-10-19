# VERIFIED

Command (run from `prototype/`):
`PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider -v --color=no tests` (full output saved in
`test_output.txt`). Summary line:

```
============================== 61 passed in 1.00s ==============================
```

(An earlier identical run, `-q`, printed `61 passed in 8.19s`.) No test was skipped, failed or edited to pass.

The original `router_dist.py` was executed read-only in a subprocess with `../venv/bin/python3 -B` and
`PYTHONDONTWRITEBYTECODE=1`, cwd = repo root, calling only `Bucket`, `BetaBucketModel.posterior`, `decide`,
`simulate`, `task_record` (and, in one test, the read-only loader `router_dist.load` + `BetaBucketModel.fit`).

| feature | state | evidence |
|---|---|---|
| Load frozen model (`data/bucket_model.json`) | TESTED | byte-identical to `results/router_dist/bucket_model.json` (sha256 in `data/SOURCE.md`); `test_frozen_model_matches_fresh_fit_by_router_dist` (fresh fit on all 24 tasks by router_dist: n, s, cost, cost SE and `c_bar` equal) |
| Posterior mean and SD per architecture | TESTED | `test_recommendation_and_posterior_match_router[w-λ]` for w ∈ {1,2,4,3(empty)} × λ ∈ {0,10,100,300} (equal to 1e-12); `test_hand_computed_posterior_means[1,2,4]` |
| Utility mu − λ·cost and recommended architecture | TESTED | same parametrized test (pick, tied set); `test_hand_computed_picks` (12 cases, all match the expected picks given in the task) |
| Tie-break (lower cost, then SA, WF, MA) | TESTED | empty-bucket cases are exact three-way ties: `test_empty_bucket[λ-3/5]` (tied = all three, pick SA) and the router comparison for width 3; no tie occurs in a populated bucket at the tested λ |
| Empty-bucket behaviour (Beta(1,1), fallback cost, "no evidence") | TESTED | `test_empty_bucket` (widths 3 and 5, 4 λ each); width 3 compared with the original (flag, default, pick, mean, SD, cost) |
| P(best) of the recommended architecture (5000 draws, fixed seed) | TESTED | `test_pbest_and_interval_match_router[w-λ]` (exact equality with the original, same seed key 0) |
| 95% credible interval of the utility gap, "no clear winner" flag | TESTED | same test (equal to 1e-12; flag equal) |
| Evidence flag / default-pick flag | TESTED | `test_recommendation_and_posterior_match_router` (flag, is_default equal to the original) |
| P(best) for the two non-recommended architectures | IMPLEMENTED, UNVERIFIED against the original | the original does not expose it; computed from the same draws |
| Evidence counts (categories and tasks per width) | IMPLEMENTED; categories TESTED | category count comes from the model (tested); task ids/counts come from `data/bucket_evidence.json` built by `tools/make_evidence.py` (counts agree with the model's categories: w1 20/15, w2 2/2, w4 2/1; not covered by a test) |
| App renders, responds to width and λ (slider and quick buttons), empty widths show "NO EVIDENCE" | TESTED | `tests/test_app.py` (AppTest, headless): `test_renders_default`, `test_slider_changes_recommendation`, `test_quick_button_and_width`, `test_empty_width_shows_no_evidence[3,5]` |
| App served over HTTP | TESTED (smoke only) | `streamlit run app.py --server.headless true --browser.gatherUsageStats false --server.address 127.0.0.1 --server.port 8765`: `/_stcore/health` returned `ok`, `/` returned HTTP 200; server stopped afterwards (pgrep found no process) |

## Not verified
- The visual layout in a real browser (no browser was opened; AppTest checks elements, not appearance).
- P(best) values for the two non-recommended architectures against the original (not exposed by it).
- Behaviour for inputs outside the tested grid (other λ values between 0 and 300 are computed with the same code
  but were only exercised through the slider test at λ = 100 and the grid above).
- `data/bucket_evidence.json` task lists against any other source than the decomposition cache.
- That P(best) shown in the app equals any per-task value in `results/router_dist/report.txt`: it does not by
  design (different seed stream key; see DECISIONS.md D2).
- Anything about real-world performance of the recommendation (out of scope; the router is not validated).
