# DECISIONS (v2) — Checkpoint 1

## V2-D1. Separate environment `prototype/.venv_v2` (approved)
`requirements_v2.txt` pins numpy 2.0.1, streamlit 1.66.0, pytest 9.1.1 (same as `.venv`) plus the research decomposer's
dependencies at the research venv's versions: litellm 1.67.2, networkx 3.5. `.venv` (v0/v1) was not touched.
`.venv_v2` is made self-ignoring with `.venv_v2/.gitignore` (`*`) so the v0 `prototype/.gitignore` did not need editing.

## V2-D2. Reuse of the research decomposer without modifying it
`live_decompose.py` imports `decomposition/decompose.py` by file path (`importlib`, module name `research_decompose`)
and uses `SYSTEM_PROMPT`, `_decompose_with_retries`, `compute_features`, `DecompositionError`, `DEFAULT_MODEL`.
Call: `_decompose_with_retries(query, model=DEFAULT_MODEL, temperature=0.0, max_retries=3)` = `decompose_task`'s
defaults, i.e. the settings of the 24 cached DAGs. `decompose_task` is never called (it writes to
`decomposition/cache/`); the tests replace it with a function that fails if called.

## V2-D3. Pre-import safety settings (found during the read-only review)
litellm 1.67.2 calls `dotenv.load_dotenv()` at import when `LITELLM_MODE` is `DEV` (its default) and downloads its
price table from GitHub at import unless `LITELLM_LOCAL_MODEL_COST_MAP` is set. `load_decomposer()` sets
`LITELLM_MODE=PRODUCTION` and `LITELLM_LOCAL_MODEL_COST_MAP=True` (unconditionally, in this process only), sets
`sys.dont_write_bytecode` during the import, and sets `litellm.telemetry = False`. A negative-control test shows the
unguarded import does call `load_dotenv` and does attempt a network connection; the guarded import does neither.

## V2-D4. Pin of the research file
`decompose.py` sha256 `4bcf6602accbab788cbf2916e45e8dc3fa7f4539c99f8b06228c058ae80c455b` (last commit `1e7e83b`).
Checked before import and on every later call; on mismatch the live path raises `DecomposerUnavailable` and the
examples and manual width keep working.

## V2-D5. In-memory completion seam
`decompose.completion` (the name the research module imported from litellm) is replaced, in this process only, by
`CompletionSeam`, which forwards to litellm, adds `timeout=60` s, counts attempts and records `response_cost`. Tests
swap its backend for a fake. The research file is not changed.

## V2-D6. Task text and optional context
`compose_query(task, context)`: no context → exactly the stripped task text (research setting); with context →
`task + "\n\n" + "Additional context provided by the user:" + "\n" + context`, flagged `context_included` with a note
that the input differs from the research setting. Limits: 2,000 characters each; empty task rejected before any call.
Leading/trailing whitespace of the task is stripped (the research queries have none).

## V2-D7. Two width calculations vs correctness
Every generation computes width with research `compute_features` (networkx) and with prototype `dag_width`
(pure Python); disagreement rejects the result (`width_mismatch`). The stored text states that agreement confirms the
width is computed consistently for that DAG, not that the decomposition is correct.

## V2-D8. Privacy injection not applied to custom tasks
No benchmark category → no code-level refusal-check injection. Noted on every generation. Checked read-only: removing
the refusal-check node from the four privacy DAGs leaves their width at 1.

## V2-D9. State (memory only)
`v2_state.py` wraps `v1_state` (unchanged): generations are kept in `state["v2_generations"]` keyed by the sha256 of
the composed input; `v2_history` lists widths across regenerations of the current input; `v2_confirmed` records the
confirmed width, its source (generated / manual override) and the generated width. A (re)generation always clears the
confirmation and the recommendation request; editing text or context clears the generation association; a generation
for a stale input or while an example is selected is rejected. Nothing is written to disk.

## V2-D10. API key handling
`generate()` checks only that `OPENAI_API_KEY` is present; it never reads, prints or stores its value, and error messages
are passed through a redaction of `sk-…` patterns. No API key was present in this session's environment, so the live
smoke test (T15) was skipped (see VERIFIED_V2.md).

## V2-D11. Test correction during development
`test_T10_generations_write_nothing` first asserted that `decomposition/__pycache__/` does not exist. It does exist,
from the research runs (files dated 2026-09-12 and 2026-09-24, listed in `repo_state/v2_before.txt`). The assertion was
replaced by a check that those files are present and unchanged; the full-tree snapshot comparison (no added, removed or
changed files) was already part of the test and was not relaxed.

## V2-D12. Future deployment concern: shared attempt counter (not addressed in the MVP)
`live_decompose` keeps one module-level `CompletionSeam` per Python process, and `generate()` resets its call list at
the start of each generation. Streamlit runs every browser session in the same process, so two sessions generating at
the same time could interleave and report each other's attempt counts and costs. The DAG and width returned to each
session are not affected (they come from each call's own return value), only the `attempts` and `cost_usd` fields.
This is acceptable for the single-user local demo. A multi-user deployment would need a per-call counter (e.g. a seam
object created per generation, or a lock around `generate()`). Out of scope for the V2 MVP by decision.

# DECISIONS (v2) — Checkpoint 2

## V2-D13. App structure (`app_v2.py`, run with `.venv_v2`)
Three stages as in v1. Stage 1: selector with v1's benchmark and illustrative examples, the recorded generated examples
and "Custom task"; task text; optional context box (only for custom/recorded tasks). Stage 2: stored DAG for examples
(as v1); for custom/recorded tasks a "Generate DAG with LLM" / "Regenerate DAG" button, the generated DAG table, width
(with both calculations and the meaning of their agreement), provenance and notes, a changed-width warning across
regenerations, "Use generated width (w)", and a manual correction ("Use this width instead"). Without a generation, the
v1 manual-width path stays available. Stage 3: lambda and the recommendation exactly as v1, plus the width source.

## V2-D14. Lazy API client
`app_v2.py` imports `live_decompose`, which does not import litellm until `load_decomposer()` runs on the first
"Generate". Without an API key the button is disabled and an info message explains the alternatives. Verified by T20.

## V2-D15. Recorded demonstration examples
`tools/record_v2_examples.py` ran once with the live path (4 real calls, all valid on the first attempt) for four NEW
CRM queries (not benchmark tasks): complaint + renewal (width 2), new-lead BANT qualification (width 4), delivery-delay
summary (width 1) and region pipeline vs revenue with user context (width 2). Stored in `data/v2_recorded_examples.json`
with full provenance and labelled "Recorded LLM-generated example — not evaluated". Selecting one loads its text, context
and generation into the custom path; the user still confirms the width. No API call at runtime.

## V2-D16. Checkpoint 1 bug fixed in Checkpoint 2
`v2_state.record_generation` read `gen.input_hash` before converting a stored generation dict, so recorded examples
(dicts) raised `AttributeError`. Fix: convert first, then compare `d["input_hash"]` (3 lines). This is the only change to
a Checkpoint 1 file (`repo_state/v2_cp2_frozen_cp1_hashes.txt` shows `v2_state.py` changed, the other 7 unchanged). All
Checkpoint 1 tests still pass.
