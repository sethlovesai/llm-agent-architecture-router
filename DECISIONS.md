# DECISIONS

## D1. Mode: ADAPTER (not IMPORT)
Importing `router_dist.py` is side-effect-free apart from bytecode caching and needs only numpy (see
`INSPECTION.md`), so IMPORT mode was possible in principle. ADAPTER mode was chosen because:
1. The README launch command (`cd prototype && .venv/bin/streamlit run app.py`) does not set
   `PYTHONDONTWRITEBYTECODE`; importing `router_dist`, `router`, `oracle`, `normalize_score` and `task_tiers`
   from the repo root would write `__pycache__/*.pyc` OUTSIDE `prototype/` every time a user runs the app.
2. P(best), the credible interval and the flags are computed inside `task_record`, which also needs a task
   object with observed quality and cost (for regret against the oracle). Calling it from the app would need a
   fake task object; a small adapter is cleaner and keeps the app independent of the research tree.
3. The app then depends only on the frozen `data/bucket_model.json` and on numpy, not on `results/`.

The original is still used as the reference: the tests run it read-only in a subprocess with the research
environment's existing interpreter (`../venv/bin/python3`, execute only) with `-B` and
`PYTHONDONTWRITEBYTECODE=1`, and compare outputs (see `VERIFIED.md`).

### Duplicated calculations (adapter ⇄ original)
| adapter (`router_adapter.py`) | original (`router_dist.py`, commit a2fce62) |
|---|---|
| `Bucket.alpha/beta/mu/sd` | `Bucket.alpha/beta/mu/sd` (88-110) |
| `FrozenModel.posterior` (empty bucket: n=0, s=0, cost = `c_bar` for all, SE None) | `BetaBucketModel.posterior` (155-158) |
| `decide` (U, exact tie < 1e-9, tie-break lower cost then SA<WF<MA) | `decide` (161-165) |
| `simulate` (5000 draws, `default_rng([20261006, key])`, Beta then standard normal draws, clip at 0) | `simulate` (168-175) |
| P(best) of the selected architecture, 95% gap interval, "no clear winner", evidence flag, default flag | `task_record` (178-207) |
| constants `ARCHS`, `DRAWS=5000`, `SEED=20261006`, `TIE_EPS=1e-9` | `router.py` 91-103 |
The model FIT (category means, cost SE, `c_bar`) is NOT duplicated: the adapter only reads the frozen fitted
values from `data/bucket_model.json`.

## D2. Seed stream key
`router_dist.simulate` seeds each task with `default_rng([20261006, task_id])`. The app has no task id, so it
uses the fixed key `0` (`router_adapter.DEFAULT_SEED_KEY`). The tests call the original with the same key, so
P(best) and the interval are compared like for like. P(best) values in the app therefore are not the same
numbers as the per-task P(best) in `results/router_dist/report.txt` (those use each task's id as key).

## D3. P(best) for all three architectures
The original reports P(best) only for the selected architecture. The app table shows, for every architecture,
the share of the same 5000 draws in which it has the highest utility (`P_best_each`); the value for the
recommended architecture is exactly the original's P(best) (tested). The other two values are an addition
(computed with the same `argmax`, not compared with the original, because it does not expose them).

## D4. Empty-bucket cost
The original's empty-bucket cost is the training set's `c_bar`. For the final all-24 model that is the stored
`empty_bucket_cost_fallback_c_bar` (0.0023221…); the app uses it for widths 3 and 5 (and any width not in the
model). Under cross-validation the original used each fold's own `c_bar`, which is not relevant to the app.

## D5. Width input range and evidence counts
Width input is 1-5 (as requested). Widths with data: 1, 2, 4. "Tasks behind the bucket" is not in
`bucket_model.json`, so `tools/make_evidence.py` froze task ids and categories per width from
`decomposition/cache/*.json` (read-only; same width rule as `router.load_tasks`: `parallelism_width`, or 1
when absent) into `data/bucket_evidence.json` (with a sha256 of the cache files). It agrees with the model's
category counts (w1: 20 tasks / 15 categories, w2: 2 / 2, w4: 2 / 1).

## D6. Dependencies
`requirements.txt`: `numpy==2.0.1` (pinned to the research environment's version so the random streams are the
same generator implementation as the original's), `streamlit` (installed 1.66.0), `pytest` (installed 9.1.1).
Installed only into `prototype/.venv` (Python 3.12.10). pandas comes with streamlit.

## D7. Baseline snapshot timing
`repo_state/before.txt` was written by redirecting into a file under `prototype/repo_state/`, so the directory
`prototype/repo_state/` had to exist first and the snapshot lists `before.txt` itself as untracked. Nothing
else under `prototype/` existed at that point.

## D8. Pre-existing files
`report9.txt` and `review_900002.md` were already COMMITTED on the current branch `prototype` (commit
`4ee3f05`, "Add data-pull report and 900002 review") before this work started, so they do not appear as
untracked in either snapshot.

## D9. Streamlit user config
Streamlit uses `~/.streamlit/` in the user's home directory (outside the repo). It already existed
(`credentials.toml`, `machine_id_v4`, dated 2025-06-11) and was not changed by this work (checked by listing).
The test server was started with `--server.headless true --browser.gatherUsageStats false --server.address
127.0.0.1 --server.port 8765` and stopped afterwards.
