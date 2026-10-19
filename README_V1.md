# CRM task-aware architecture recommendation prototype (v1)

## Launch
```
cd prototype && .venv/bin/streamlit run app_v1.py
```
v0 is unchanged and still runs with `.venv/bin/streamlit run app.py`.

## Tests
```
cd prototype
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider -q tests_v1   # v1: 70 tests
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider -q tests      # v0: 61 tests
```

## What it does
It demonstrates the research pipeline **CRM task → task decomposition → DAG width → Bayesian router → architecture
recommendation** for stored examples, and keeps a manual path for any other task:
1. **Describe your CRM task.** Pick one of five examples (four benchmark tasks, one illustrative) or "Custom task",
   and see or type the description.
2. **Review task structure.** For an example, the stored DAG (subtasks, roles, dependencies) is shown and its width is
   computed from the dependencies. For a custom task you choose a width (1-5) and confirm it explicitly.
3. **Architecture recommendation.** With a cost preference lambda (0-300; quick buttons 0, 10, 100, 300) the frozen
   width-only Bayesian router (v0, unchanged) recommends Single-Agent, Workflow or Multi-Agent and shows estimated
   quality ± SD, cost per run, expected utility, chance of being best, the 95% interval of the recommendation's
   utility advantage, "no clear winner" / "no evidence" / limited-evidence warnings, a plain-English explanation and
   the evidence behind the width.

## What it does NOT do
- It does not analyse, understand or decompose free text. Custom text is shown back to you and ignored by the router.
- It does not execute Single-Agent, Workflow or Multi-Agent, call any model or API, or connect to a CRM.
- It is not a validated router: in the project's evaluation the width-only router **did not outperform the best fixed
  strategy**. It reproduces that router's recommendation from a width and a cost preference.

## Benchmark vs illustrative examples
- **Benchmark example — in sample** (tasks 900002, 89, 2056, 722): description and DAG copied verbatim from the cached
  decomposition used in the evaluation (`decomposition/cache/<id>.json`, sha256 recorded in `data/v1_examples.json`).
  These tasks are part of the 24 the router was fitted on, so they are not unseen validation tasks.
- **Illustrative example** (customer health check, width 3): authored to demonstrate the interface and the
  empty-bucket behaviour. Its DAG is hand-written and it has no evaluated evidence.

## Why custom tasks need a manual width
Automatic decomposition in the research code needs an LLM call, which this prototype does not make. So the app never
infers width from text (no keywords, regex, text length or embeddings). The width box starts empty, a width counts
only after "Confirm width", and any edit to the text clears the confirmation. Editing an example's text turns it into
a custom task and detaches its stored DAG, so a stored DAG is never attached to text it does not belong to.

## How width is computed for stored DAGs
`dag_width.py` (pure Python) follows `decomposition/decompose.py`: every subtask is a node (all roles counted), each
`depends_on` entry is an edge, and the width is the size of the largest set of subtasks with no dependency path between
any two of them (largest antichain of the transitive closure). An undecomposed task has width 1, as in the router.
The function reproduces the stored width of **all 24** cached benchmark DAGs (test `test_all_24_cached_dags_match_stored_width`).

## User journey (for the report and video)
1. Open the app: the example "Flag accounts with an open support case AND a recent order" (benchmark task 900002, in
   sample) is selected. Step 2 shows its DAG: two independent retrievals feeding one analysis and one response, so the
   computed width is **2**.
2. Click **Get recommendation**: at lambda 0 the router recommends **Multi-Agent**, with a "no clear winner" warning.
3. Click **lambda = 300**: the recommendation switches to **Single-Agent** because cost now weighs more; the
   explanation says Multi-Agent has higher estimated quality but Single-Agent's lower cost gives it higher utility.
4. Choose **Custom task** and type your own task: the app says decomposition is not available. Choose a width (e.g. 3),
   click **Confirm width**, then **Get recommendation**: width 3 has no evidence, so the app shows the router's
   tie-break default with a "No evidence" warning. Edit the text and the confirmation is cleared.

## Known limitations
- 24-task benchmark, 11 informative tasks, 3 repeats; buckets are sparse (width 4: one category; width 2: two).
- Chance of being best is a model-based estimate, not a guarantee; at width 4 it can approach 100% because cost
  uncertainty is not estimated with one category.
- Benchmark examples are in-sample. The illustrative example is not evidence.
- The privacy-task scores in the underlying benchmark are confounded (see the project's audit); the router uses them.
- Visual appearance was not checked in a real browser (see VERIFIED_V1.md).
