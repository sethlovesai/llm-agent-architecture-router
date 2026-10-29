import json
import math
import os
from dataclasses import dataclass

import numpy as np

ARCHS = ["single_agent", "workflow", "multi_agent"]   # router.py ARCHS order (also the tie-break priority)
SHORT = {"single_agent": "SA", "workflow": "WF", "multi_agent": "MA"}
DRAWS = 5000                                           # router.py MC_DRAWS
SEED = 20261006                                        # router.py SEED
TIE_EPS = 1e-9                                         # router.py TIE_EPS
DEFAULT_SEED_KEY = 0   # router_dist seeds per task as default_rng([SEED, task_id]); the app has no task id, so it uses 0

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(HERE, "data", "bucket_model.json")
EVIDENCE_PATH = os.path.join(HERE, "data", "bucket_evidence.json")


@dataclass
class Bucket:
    n: int                 # number of training categories (evidence units)
    s: np.ndarray          # soft success totals per architecture
    chat: np.ndarray       # expected cost per run (USD) per architecture
    se: object             # cost standard errors (np.ndarray) or None when unavailable

    @property
    def alpha(self):
        return 1.0 + self.s

    @property
    def beta(self):
        return 1.0 + self.n - self.s

    @property
    def mu(self):
        return (1.0 + self.s) / (2.0 + self.n)

    @property
    def sd(self):
        return np.sqrt(self.mu * (1 - self.mu) / (self.n + 3.0))


class FrozenModel:
    def __init__(self, path=MODEL_PATH):
        with open(path) as f:
            raw = json.load(f)
        self.raw = raw
        self.c_bar = float(raw["empty_bucket_cost_fallback_c_bar"])
        self.n_tasks_fitted = raw["n_tasks_fitted"]
        rows = {}
        for e in raw["bucket_model"]:
            w = int(e["bucket"].strip("()w"))
            rows.setdefault(w, {})[e["architecture"]] = e
        self.buckets = {}
        for w, by_arch in rows.items():
            es = [by_arch[a] for a in ARCHS]
            n = {e["n"] for e in es}
            assert len(n) == 1, f"inconsistent n in bucket w{w}"
            se = None if any(e["cost_se"] is None for e in es) else np.array([e["cost_se"] for e in es], float)
            self.buckets[w] = Bucket(n.pop(), np.array([e["soft_success_total_s"] for e in es], float),
                                     np.array([e["expected_cost"] for e in es], float), se)

    def widths(self):
        return sorted(self.buckets)

    def posterior(self, width):
        """Empty bucket: Beta(1,1) for all three and the global cost fallback for all three."""
        if width in self.buckets:
            return self.buckets[width]
        return Bucket(0, np.zeros(3), self.c_bar * np.ones(3), None)


def decide(mu, chat, lam):
    U = mu - lam * chat
    tied = [i for i in range(3) if U.max() - U[i] < TIE_EPS]
    pick = sorted(tied, key=lambda i: (chat[i], i))[0]   # lower cost, then SA < WF < MA
    return ARCHS[pick], [ARCHS[i] for i in tied], U


def simulate(b, seed_key=DEFAULT_SEED_KEY):
    rng = np.random.default_rng([SEED, seed_key])
    q = rng.beta(b.alpha, b.beta, size=(DRAWS, 3))
    z = rng.standard_normal((DRAWS, 3))
    se = np.zeros(3) if b.se is None else b.se
    c = np.clip(b.chat + z * se, 0.0, None)
    return q, c


def recommend(model, width, lam, seed_key=DEFAULT_SEED_KEY):
    b = model.posterior(width)
    pick, tied, U = decide(b.mu, b.chat, lam)
    q, c = simulate(b, seed_key)
    Ud = q - lam * c
    best = Ud.argmax(axis=1)
    pi = ARCHS.index(pick)
    p_best_each = np.array([(best == i).mean() for i in range(3)])   # extra: share of draws each arch is best
    others = np.delete(Ud, pi, axis=1).max(axis=1)
    gap = Ud[:, pi] - others
    lo, hi = float(np.percentile(gap, 2.5)), float(np.percentile(gap, 97.5))
    if b.n == 0:
        flag = "no evidence (empty bucket)"
    elif len(tied) > 1:
        flag = "tie in estimate"
    elif b.n == 1:
        flag = "n=1 (cost SE unavailable)"
    else:
        flag = "ok"
    return {
        "width": width, "lambda": lam, "n_categories": b.n, "pick": pick, "tied": tied,
        "mu": b.mu, "sd": b.sd, "cost": b.chat, "cost_se": b.se, "utility": U,
        "P_best": float(p_best_each[pi]), "P_best_each": p_best_each,
        "gap_lo": lo, "gap_hi": hi, "no_clear_winner": lo <= 0.0 <= hi,
        "flag": flag, "is_default": flag in ("no evidence (empty bucket)", "tie in estimate"),
        "no_evidence": b.n == 0,
    }


def load_evidence(path=EVIDENCE_PATH):
    """Task ids / categories per width (frozen from the decomposition cache; see data/SOURCE.md)."""
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        return {int(k): v for k, v in json.load(f)["widths"].items()}
