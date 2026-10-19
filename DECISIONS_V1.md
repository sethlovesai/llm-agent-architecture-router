# DECISIONS (v1)

## V1-D1. v0 left untouched; v1 is additive
New files only: `app_v1.py`, `dag_width.py`, `v1_state.py`, `v1_explain.py`, `data/v1_examples.json`,
`tools/make_v1_examples.py`, `tests_v1/`, `README_V1.md`, `VERIFIED_V1.md`, `DECISIONS_V1.md`, `repo_state/v1_*`,
`test_output_v1.txt`, `test_output_v0_after_v1.txt`. v1 imports `router_adapter.py` (unchanged) and reads
`data/bucket_model.json` and `data/bucket_evidence.json` (unchanged). Hashes of the protected v0 files were recorded
before work (`repo_state/v1_protected_hashes_before.txt`) and are re-checked by a test and at the end.
v1 tests live in `tests_v1/` so the v0 command (`pytest tests`) still runs exactly the 61 v0 tests.

## V1-D2. Width definition (read from decomposition/decompose.py, not imported)
`decompose.py` imports `litellm` and `networkx`, so it is not imported. Its definition, re-implemented in
`dag_width.py` without networkx:
- graph: one node per subtask, all roles counted (including an injected Analyst refusal check and the final
  Responder); an edge for every `depends_on` entry (`_build_graph`, decompose.py:100-112);
- `parallelism_width` = size of the largest antichain on the transitive closure, found by brute force from the
  largest size down (`compute_features`, decompose.py:247-282);
- features are only computed when `decomposition_warranted` is true (decompose.py:360); the router then uses width 1
  for an undecomposed task (`router.load_tasks`: `features.parallelism_width or 1`). `router_width()` follows that.
`depth()` (longest chain, node count) is shown for information only and is also checked against the cache.

## V1-D3. Examples (5)
Four **benchmark examples — in sample** (query, flag and subtasks copied verbatim from `decomposition/cache/<id>.json`
with the file's sha256; stored `features` kept only for provenance/tests, never used for the width shown):
900002 (width 2; its pick changes with lambda: MA at 0/10/100, SA at 300), 89 (width 4, BANT lead qualification),
2056 (width 1, sequential), 722 (undecomposed, width 1). One **illustrative example** (hand-written DAG with three
independent retrievals, width 3) shows the empty-bucket behaviour; it is labelled as authored and not evaluated.
900001 (also width 2) was not used, to keep the list at five.

## V1-D4. Task-input state machine (`v1_state.py`)
- Selecting an example loads its text and attaches its stored DAG; width is computed from that DAG.
- Selecting "Custom task" clears the text box (empty), clears any manual width, and clears a pending recommendation.
- Editing an example's text (any change so the text differs from the stored description) detaches the DAG, switches
  the selector to "Custom task", records which example it was edited from (for a notice), clears any manual width and
  the recommendation request.
- Editing custom text clears the width selection, the confirmation and the recommendation request.
- A manual width counts only after the explicit "Confirm width" action and only for the exact text it was confirmed
  for. Selecting a value in the width box alone does not count.
- Pasting an example's exact text into a custom task does NOT attach the example's DAG (custom text never maps to a
  stored DAG); text is never inspected to infer width (no keywords, regex, length or embeddings).
- "Get recommendation" is disabled until a width is available. Once requested, the recommendation stays visible while
  the user switches between examples (each has a valid stored width), so switching examples updates the DAG, width and
  recommendation together; it is hidden again whenever the width becomes unconfirmed.
- Streamlit detail: the selector and text box use widget keys (`example_select`, `task_text_input`) that are synced
  from the logical state inside callbacks (the only place Streamlit allows writing widget state).

## V1-D5. Router outputs and explanation
The recommendation calls `router_adapter.recommend(model, width, lambda)` exactly as v0 does (seed key 0), so
posterior means/SDs, costs, utility, P(best), the 95% interval, flags, tie-break and empty-bucket behaviour are v0's.
The explanation (`v1_explain.py`) is a fixed template filled from that result (no LLM): pick and cost preference; a
quality-vs-cost sentence when the pick is not the highest-quality architecture; the tie sentence; "no clear winner"
or "interval excludes zero"; the one-category warning; and a separate text for empty buckets (tie-break default).

## V1-D6. UI wording
Accessible labels: "Estimated quality (mean ± SD)", "Estimated cost (USD per run)", "Expected utility",
"Chance of being best within this model", "Strength of supporting evidence". Seeds, formulas, task ids and flags
are in expanders. A footer states the six transparency points. `width="stretch"` is used instead of the deprecated
`use_container_width` (v0's `app.py` still uses the old argument; not changed, it only prints a deprecation notice).

## V1-D7. Things noticed, not changed
- A v0 Streamlit server (`.venv/bin/streamlit run app.py`, port 8501, started 2026-10-16 13:16) was already running,
  not started by this work; it was left alone. The v1 test server (port 8766) was started and stopped.
- Width 4 and width 2 each rest on one and two categories; see the warnings in the app and README_V1.
