# Handover

Author: Seth Wing Shen Yap

## 1. What this is
Streamlit prototype (`app_v2.py`), Master's AI capstone. An LLM turns a CRM task into a subtask DAG, and a width-only Beta router recommends single-agent, workflow or multi-agent. In evaluation it did not beat the best fixed architecture.

## 2. Where things live
This repo holds the app and the frozen model only. It cannot refit the router.

Research kit: Provided separately by Seth as research-kit.zip (refit scripts, cached DAGs, per-run results, README).

It holds `router_dist.py`, `router.py`, `oracle.py`, `normalize_score.py`, `task_tiers.py`, `structured_score.py`, `decomposition/cache/` (24 DAGs) and `results/{custom_baseline,workflow,multi_agent}/` (216 run JSONs).

## 3. Key files
| File | What it does | Touch it when |
|---|---|---|
| `data/bucket_model.json` | Frozen fitted model | Every refit |
| `data/bucket_evidence.json` | Task ids and categories per width | Every refit |
| `data/SOURCE.md` | Model provenance | Every refit |
| `router_adapter.py` | Loads the model, recommends | Router logic changes |
| `app_v2.py` | The interface | Interface changes |
| `live_decompose.py` | Decomposer bridge, holds the pin | `decompose.py` changes |
| `research/decompose.py` | Verbatim research decomposer | Leave alone: pinned by sha256 |

## 4. Retrain on new data
Work in a copy of the kit.
1. Refit: Python 3 with numpy (tested: 3.12.10, 2.0.1). New experiments: `pip install -r requirements.txt` and `pip install datasets`. [verified by running]
2. Name runs `results/custom_baseline/results_gpt-4o-mini_react_task{id}_run{n}.json` (`workflow/…_workflow_…`, `multi_agent/…_multi_agent_…`), per `oracle.py:110-113`. A misnamed file raises `missing data` (`router.py:144`). [verified by running]
3. Add `decomposition/cache/{id}.json` and all three architectures' results per new task. `decompose_task()` (`decomposition/decompose.py:319`) creates it, with an LLM key. `TASK_IDS` in `architectures/run_workflow_batch.py:21` omits 900001 and 900002; add them to rerun workflow on custom tasks. [verified by reading code]
4. Add the task to `TASK_TIERS` (`task_tiers.py:19`). If missing, tier is "unknown"; fit unchanged. [verified by running]
5. Edit `router_dist.py:322` (`== 11` scored) and `:324` (`== 13` excluded). Excluded = all architectures tie on quality (`oracle.py:267`). [verified by running]
6. Copy `report.txt` aside, then run `python3 router_dist.py` (offline). [verified by running, network blocked]
7. Outputs: `results/router_dist/bucket_model.json`, `report.txt`, `summary_all.csv`, `per_task_headline_LOCO.csv`, `comparison_with_router_py.csv`. Unmodified data gives sha256 `90066740b062f0fc9566ce3ee98d78fcc2a0cb4cb1b424890f038f5eb9215d38`. [verified by running]

## 5. Update the prototype after a refit
1. Copy the new `bucket_model.json` to `data/`.
2. Hand-edit `data/SOURCE.md` (source, commit, both sha256, copy time); no script writes it. [verified by reading code]
3. In the kit, `prototype/tools/make_evidence.py` writes `prototype/data/bucket_evidence.json` and `make_v1_examples.py` writes `prototype/data/v1_examples.json`, offline from `decomposition/cache/`. Create `prototype/data/` first; copy both into `data/` here. `v2_recorded_examples.json` is demo-only; no regeneration needed. [verified by reading code]
4. `app_v2.py:160` and `:275` hard-code "24 tasks". [verified by reading code]
5. If `research/decompose.py` changes, update `PINNED_SHA256` and `PINNED_COMMIT` (`live_decompose.py:15-16`) or live decomposition is disabled. [verified by reading code]

## 6. Watch-outs
- Width 2 has 2 categories and width 4 has 1; those buckets are thin.
- 13 of 24 tasks scored zero for every architecture and are excluded from regret.
- Privacy scores come from an LLM judge that sees refusal-check text: unreliable.
- Licence: CC BY-NC 4.0, non-commercial only (`NOTICE.md`).
