# INSPECTION (read-only, step 1)

Sources read: `CLAUDE.md`, `results/router_dist/SPEC.md`, `router_dist.py`, and the modules it imports
(`router.py`, `oracle.py`, `normalize_score.py`, `task_tiers.py`, `structured_score.py`). `.env` was not read.

## Where the fitted model lives
- `results/router_dist/bucket_model.json` (last commit `a2fce62`, unchanged against HEAD). It is the FINAL
  width-only model fitted on all 24 tasks after the cross-validation (`n_tasks_fitted: 24`, `n_categories: 18`,
  `headline_definition: "width"`). The headline buckets are in `bucket_model` (w1, w2, w4; 3 architectures each);
  `empty_bucket_cost_fallback_c_bar` = 0.0023221305555555555; the variants are in `variants` (not used here).
- Frozen copy: `prototype/data/bucket_model.json` (byte-identical, sha256 in `data/SOURCE.md`).

## Where each computation lives in router_dist.py (commit a2fce62)
| computation | location |
|---|---|
| posterior Beta params, mean `(1+s)/(2+n)`, SD `sqrt(mu(1-mu)/(n+3))` | `Bucket` dataclass, properties `alpha`, `beta`, `mu`, `sd` (`router_dist.py:88-110`) |
| fitting the buckets (category means, cost mean and SE, `c_bar`) | `BetaBucketModel.fit` (`router_dist.py:119-152`) |
| empty-bucket fallback (n=0, Beta(1,1), cost `c_bar` for all three, SE None) | `BetaBucketModel.posterior` (`router_dist.py:155-158`) |
| utility `U = mu - lambda*c_hat`, exact tie (< 1e-9), tie-break lower cost then SA, WF, MA | `decide` (`router_dist.py:161-165`) |
| Monte Carlo, 5000 draws, `default_rng([20261006, task_id])`, quality ~ Beta, cost ~ Normal(c_hat, SE) clipped at 0 | `simulate` (`router_dist.py:168-175`) |
| P(best) (share of draws where the selected architecture has the highest U), 95% interval of U(selected) − max U(others), "no clear winner" (interval includes 0), evidence flag, default flag | `task_record` (`router_dist.py:178-207`) |
| constants `MC_DRAWS=5000`, `SEED=20261006`, `TIE_EPS=1e-9`, `ARCHS` order | `router.py:91-103` (imported by router_dist.py:34-37) |

`task_record` also needs a task object (it calls `router.oracle_pick(t, lam)` and `router.actual_U`, which read
the task's observed quality and cost) because it computes regret against the oracle; P(best) and the interval
do not depend on that part.

## Import-safety assessment
Import chain of `router_dist.py`:
- stdlib: `glob, hashlib, json, math, os, subprocess, dataclasses, collections` (router_dist); `argparse, csv,
  sys` (router); `argparse, glob, json, os, statistics` (oracle); `glob, json, sys, collections` (normalize_score).
- third-party: **numpy only** (router_dist, router). `structured_score` (stdlib `re`, `argparse`) is imported
  lazily inside `oracle._run_quality`, only when scoring tasks 900001/900002.
- sibling modules: `oracle`, `router`, `normalize_score`, `task_tiers` (and lazily `structured_score`).
- **No** `dotenv`/`load_dotenv`, **no** `litellm`/`openai`/`simple_salesforce`, no `crm_sandbox` import anywhere
  in the chain (checked by grepping every import line of the five modules).
- Module-level code (checked with an AST scan of top-level statements): only constant assignments
  (paths built with `os.path`, dicts, `np.geomspace` in router.py:102, an `assert` in task_tiers.py:52); every
  script body is behind `if __name__ == "__main__"` (router_dist.py:529, router.py:1208, oracle.py:544,
  normalize_score.py:138). Importing reads and writes no files, **except** that a normal import writes
  `__pycache__/*.pyc` next to those modules (outside `prototype/`) unless `PYTHONDONTWRITEBYTECODE=1` / `-B` is set.
- Functions that DO touch the filesystem (never called by the prototype): `router_dist.main` (writes
  `results/router_dist/`), `router_dist.load` / `oracle.*` (read results and the decomposition cache),
  `router_dist.file_fingerprint` / `git_changed` (read files, run `git diff`).

**Conclusion:** importing is side-effect-free apart from bytecode caching, and needs only numpy. The mode choice
(ADAPTER) and its reasons are in `DECISIONS.md`.
