# VERIFIED (v1)

## Test runs (from `prototype/`, all with `PYTHONDONTWRITEBYTECODE=1 ... -p no:cacheprovider`)
| suite | when | command | exact summary |
|---|---|---|---|
| v0 (`tests/`) | before any v1 work | `.venv/bin/python -m pytest -q tests` | `61 passed in 1.40s` (`repo_state/v0_tests_before_v1.txt`) |
| v1 (`tests_v1/`) | after implementation | `.venv/bin/python -m pytest -v tests_v1` | `70 passed in 1.54s` (`test_output_v1.txt`) |
| v0 (`tests/`) | after implementation | `.venv/bin/python -m pytest -v tests` | `61 passed in 0.96s` (`test_output_v0_after_v1.txt`) |

v1 tests by file: `test_v1_dag_width.py` 18, `test_v1_state.py` 29, `test_v1_app.py` 16, `test_v1_safety.py` 7.
No test failed, was skipped, or had its expected values changed. No v0 test was edited.

Server smoke test: `streamlit run app_v1.py --server.headless true --browser.gatherUsageStats false --server.address
127.0.0.1 --server.port 8766` → `/_stcore/health` = `ok`, `/` = HTTP 200; the server was stopped afterwards.

## Features
| # | feature | state | evidence |
|---|---|---|---|
| 1 | Each predefined example loads its stored description and DAG | TESTED | `test_each_example_loads_text_dag_and_width[5 examples]` (AppTest: text box, DAG table subtasks/dependencies, origin label); `test_select_example_loads_text_and_dag`; `test_examples_file_matches_cache_and_labels` (benchmark text and subtasks equal the cache, sha256 equal) |
| 2 | Width computed from DAG dependencies | TESTED | `test_width_unit_cases` (7 graphs incl. transitive dependency), `test_invalid_dags_raise` (cycle, unknown dependency, duplicate id), `test_undecomposed_is_width_1`, `test_example_widths` |
| 3 | Width matches the cached benchmark values | TESTED, **24 of 24** DAGs | `test_all_24_cached_dags_match_stored_width`: 23 decomposed DAGs equal `features.parallelism_width` (and `critical_path_depth`); 722 (undecomposed, no stored features) = 1 as in the router; all 24 equal v0's per-width task lists |
| 4 | Selecting a different example updates DAG, width and recommendation | TESTED | `test_switching_example_updates_recommendation`, `test_switching_examples_changes_width` |
| 5 | Editing example text invalidates its DAG and requires a new width | TESTED | `test_editing_example_text_requires_new_width` (AppTest), `test_editing_example_text_invalidates_dag` |
| 6 | Custom width starts unselected | TESTED | `test_custom_flow_requires_explicit_confirmation`, `test_custom_width_starts_unselected_and_needs_confirmation` |
| 7 | No recommendation for custom text until a width is explicitly confirmed | TESTED | same two tests (button disabled with a chosen-but-unconfirmed width; enabled only after "Confirm width"); `test_confirm_without_choice_fails` |
| 8 | Editing custom text clears the confirmation | TESTED | `test_editing_custom_text_clears_confirmation` (AppTest and pure) |
| 9 | Text alone never influences the router (width, lambda fixed) | TESTED | `test_text_does_not_affect_router[5 widths × 4 lambdas]`, `test_text_never_infers_width`, `test_pasting_exact_example_text_into_custom_does_not_attach_dag` |
| 10 | Changing lambda updates utility and the recommendation | TESTED | `test_lambda_changes_utility_and_pick_for_900002` (MA, MA, MA, SA at 0/10/100/300; utility = mean − λ·cost), `test_lambda_changes_recommendation_for_900002` (AppTest, quick buttons and slider at 250) |
| 11 | Empty-width buckets keep the v0 fallback and warnings | TESTED | `test_empty_width_keeps_v0_fallback_and_warnings[3,5]` |
| 12 | Posteriors, P(best), intervals, tie-break match v0 | TESTED | v1 calls the unchanged `router_adapter.recommend`; `test_displayed_numbers_equal_v0_adapter` checks every displayed number and the explanation against it for λ 0/10/100/300; the adapter itself is checked against the original `router_dist.py` by the unchanged v0 suite (61 passed after v1) |
| 13 | App renders and responds headlessly | TESTED | all `test_v1_app.py` tests (AppTest) plus the server smoke test |
| 14 | No prohibited imports or network calls | TESTED | `test_no_prohibited_imports[5 files]` (AST scan for litellm, openai, anthropic, simple_salesforce, dotenv, requests, httpx, socket, http, urllib, decomposition, crm_sandbox, networkx, router_dist…); `test_app_makes_no_network_connections` (socket connect blocked during an AppTest session: 0 attempts; no API module loaded) |
| 15 | Protected v0 files unchanged | TESTED | `test_protected_v0_files_unchanged` and `shasum -c repo_state/v1_protected_hashes_before.txt` at the end: all 9 OK (app.py, router_adapter.py, VERIFIED.md, README.md, data/bucket_model.json, data/bucket_evidence.json, tests/test_matches_router.py, tests/test_app.py, requirements.txt) |
| – | Plain-English explanation | TESTED (matches the result) / wording reviewed by hand | the exact `v1_explain.explain(r)` text is displayed (`test_displayed_numbers_equal_v0_adapter`); its content was checked by hand for widths 1, 2, 3, 4 at λ 0/100/300, not by an automated semantic test |
| – | Width-4 limited-evidence warning; transparency statements | TESTED | `test_width4_limited_evidence_warning`, `test_transparency_statements_present` |
| – | Accessible labels, expanders, layout | IMPLEMENTED; rendering TESTED, appearance UNVERIFIED | no real browser was used |

## Repository check
- `repo_state/v1_before.txt` vs `repo_state/v1_after.txt` (compared as sets; `git diff` does not list untracked files):
  0 entries disappeared; every new entry is under `prototype/` (the files listed in DECISIONS_V1.md V1-D1); 0 new entries
  outside `prototype/`. `git diff --name-only` and `git diff --cached --name-only` are empty in both. Branch `prototype`,
  HEAD `e7842c7` in both: no commits, pushes or branch switches. No new `__pycache__` outside `prototype/.venv/`.
- A v0 Streamlit server (port 8501, started 13:16 today) was already running and is not from this work; left running.

## Not verified / limitations
- Visual appearance and usability in a real browser.
- The explanation's wording beyond the hand-checked cases (it is a template; the numbers it uses are tested).
- That the illustrative example's DAG is a sensible decomposition (it is hand-written and labelled as such).
- Anything about real-world performance: the width-only router did not outperform the best fixed strategy in the
  evaluation; benchmark examples are in-sample.
