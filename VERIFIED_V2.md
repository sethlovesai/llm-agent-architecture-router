# VERIFIED (v2) — Checkpoint 1 (core integration and tests; no UI yet)

## Test runs (from `prototype/`, `PYTHONDONTWRITEBYTECODE=1`, `-p no:cacheprovider`)
| suite | environment | summary |
|---|---|---|
| v0 baseline (before v2 work) | `.venv` | `61 passed in 1.29s` |
| v1 baseline (before v2 work) | `.venv` | `70 passed in 1.44s` |
| v2 Checkpoint 1 (`tests_v2/`) | `.venv_v2` | `43 passed, 1 skipped in 5.96s` (`test_output_v2_cp1.txt`) |
| v0 and v1 re-run inside T14 (after implementation) | `.venv` | `61 passed` and `70 passed` (asserted by the tests) |
| T15 live smoke, `RUN_LIVE_DECOMP=1` | `.venv_v2` | `1 skipped`: **OPENAI_API_KEY not set in the environment → UNVERIFIED** (`repo_state/v2_live_smoke_result.txt`) |

By file: `test_v2_decomposer.py` 17 passed, `test_v2_state.py` 20 passed, `test_v2_safety.py` 6 passed, `test_v2_live.py`
1 skipped. No test failed in the final run. One test expectation was corrected during development (see DECISIONS_V2 D11).

## Features
| ID | feature | state | evidence |
|---|---|---|---|
| T1 | Replay of all 24 cached research DAGs through the bridge | TESTED (24/24) | `test_T1_replay_all_24_cached_dags`: width and `features` equal the stored values; both width calculations agree |
| T2 | Exact research call (system prompt, bare task text, gpt-4o-mini, temperature 0, max_tokens 2000, JSON mode, timeout) | TESTED (mocked) | `test_T2_exact_research_call` |
| T3 | Optional context appended in a fixed format and flagged | TESTED (mocked) | `test_T3_context_is_appended_and_flagged` |
| T4 | Retry with the research error feedback, then success | TESTED (mocked) | `test_T4_retry_then_success` (2 attempts recorded) |
| T5 | Invalid DAGs fail cleanly after 3 attempts, no partial state | TESTED (mocked) | `test_T5_invalid_outputs_fail_cleanly[cycle, unknown_dependency, two_sinks, sink_not_responder, invalid_role, empty]`, `test_T5_undecomposed_with_two_subtasks_and_missing_field` |
| T6 | Missing key (no call made), timeout, authentication and API errors mapped; key-like strings redacted; input limits | TESTED (mocked) | `test_T6_*` (4 tests) |
| T7 | No `.env` loading when the decomposer is imported | TESTED | `test_T7_T8_guarded_import_loads_no_dotenv_and_makes_no_network_call` (subprocess: 0 `load_dotenv` calls); negative control `test_T7_T8_control_unguarded_litellm_would_load_dotenv_and_fetch` (≥1 call without the guard) |
| T8 | No network at import | TESTED | same two tests (0 connection attempts guarded; ≥1 unguarded) |
| T9 | Hash guard on `decompose.py`; examples and manual width still work when it refuses | TESTED | `test_T9_hash_guard_refuses_changed_research_file`, `test_T9_pinned_hash_matches_research_file` |
| T10 | Generations write nothing (repo tree snapshot excluding venvs and `.git`; research cache digest) | TESTED (mocked) | `test_T10_generations_write_nothing` (0 added / removed / changed files) |
| T11 | Generated width beyond the data (6) routes as "no evidence" | TESTED (mocked) | `test_T11_width_6_routes_as_no_evidence` |
| T12 | State: generate → confirm → recommend; regenerate clears confirmation and records history; changed width flagged; override labelled; text/context edits invalidate; stale generation rejected; examples never replaced; edited example text detaches DAG; v1 manual path still works | TESTED | `test_T12_*` (8 tests) |
| T13 | Router depends only on width and lambda (generated vs manual path, widths 1/2/4 × λ 0/10/100/300) | TESTED | `test_T13_router_depends_only_on_width_and_lambda` (12 cases) |
| T14 | Protected files and cache unchanged; v0 and v1 suites unchanged | TESTED | `test_T14_protected_hashes_and_cache_unchanged` (28 files incl. `decompose.py`, router_dist.py, router.py, oracle.py, research bucket_model.json, SPEC.md, all v0/v1 files; cache digest), `test_T14_v0_suite_unchanged`, `test_T14_v1_suite_unchanged` |
| T15 | One real decomposition call | **UNVERIFIED** | skipped: `OPENAI_API_KEY` not present in this session's environment |

## What the tests do and do not establish
- All decomposition tests except T15 use a fake LLM. They verify the bridge, validation, width computation, error
  handling, state and safety; they do NOT verify the quality of any real LLM decomposition.
- Width agreement between the two calculations means consistent computation for a given DAG, not a correct decomposition.
- Not verified: a real API call (T15); latency and cost of real calls; behaviour with real litellm exception classes
  (the tests use exceptions with the same class names); concurrent Streamlit sessions sharing the module-level seam (known limitation: attempt and cost counts could mix between simultaneous sessions; DAG and width are unaffected; future deployment concern, see DECISIONS_V2 D12).

## Repository check (Checkpoint 1)
- `shasum -c repo_state/v2_protected_hashes_before.txt`: 28 OK, 0 failed. Research cache digest unchanged.
- `repo_state/v2_before.txt` vs `repo_state/v2_cp1_after.txt` (set comparison): 0 entries removed; 0 new entries outside
  `prototype/`; new entries are the Checkpoint 1 files (plus the ignored `.venv_v2`). No new `__pycache__` outside the venvs.
- Branch `prototype`, HEAD `e7842c7` before and after; nothing committed or pushed.

---

# VERIFIED (v2) — Checkpoint 2 (Streamlit V2 interface and demonstration)

## Test runs (from `prototype/`, `PYTHONDONTWRITEBYTECODE=1`, `-p no:cacheprovider`, no API key in the environment)
| suite | environment | summary |
|---|---|---|
| v2 all (`tests_v2/`, Checkpoint 1 + 2) | `.venv_v2` | `69 passed, 1 skipped in 8.80s` (`test_output_v2_cp2.txt`); skipped = T15 (opt-in live test) |
| v0 (`tests/`) | `.venv` | `61 passed in 0.83s` |
| v1 (`tests_v1/`) | `.venv` | `70 passed in 1.49s` |

By file: decomposer 17, state 20, safety 6 (includes v0/v1 re-runs and protected hashes), app 16, recorded 10 passed;
live 1 skipped (it passed when run with a key, see below).

## Real API runs (key passed only as an environment variable on the command line; never written to a file)
| run | result | evidence |
|---|---|---|
| T15 live smoke test (Checkpoint 1 follow-up) | **passed**: width 2, 1 attempt, 4 subtasks, cost $0.0002991; both width calculations agreed | `repo_state/v2_live_smoke_result.txt` (an earlier identical run's summary was lost to output filtering, so 2 real calls were made) |
| Recording 4 demo examples (`tools/record_v2_examples.py`) | 4/4 valid on the first attempt: widths 2, 4, 1, 2 (the last with context) | `data/v2_recorded_examples.json` |
| Live end-to-end UI run (AppTest, `app_v2.py`): custom task → Generate → confirm → recommend | **passed**: no error, width 2 (Retriever, Retriever, Analyst, Responder), recommendation Multi-Agent (λ 0), no exception | `repo_state/v2_live_ui_result.txt` |

## Features
| ID | feature | state | evidence |
|---|---|---|---|
| T16 | Full flow: custom text → Generate → DAG table, width, provenance → confirm → recommend; λ changes pick | TESTED (mocked) + TESTED live once | `test_T16_generate_confirm_recommend`; live UI run above |
| T16 | Context sent in the fixed format and labelled | TESTED (mocked) | `test_T16_context_is_sent_and_labelled` |
| T16 | Regenerate: changed width flagged, confirmation and recommendation cleared | TESTED (mocked) | `test_T16_regenerate_flags_changed_width_and_needs_reconfirmation` |
| T16 | Manual correction labelled and used by the router | TESTED (mocked) | `test_T16_override_is_labelled_and_used` |
| T16 | Editing text or context invalidates the generation | TESTED (mocked) | `test_T16_editing_text_or_context_invalidates` |
| T17 | No key: Generate disabled with explanation; manual path works | TESTED | `test_T17_missing_key_disables_live_path_but_rest_works` |
| T17 | Timeout / invalid output / API error: message shown, app stays usable | TESTED (mocked) | `test_T17_generation_errors_show_message_and_keep_app_usable[3]`, `test_T17_hash_guard_message` |
| T18 | Recorded examples well-formed (provenance, pin, hashes, widths recompute) and usable without a key | TESTED | `test_T18_*` (6 tests) |
| T19 | v1 benchmark and illustrative examples behave as in v1; stored DAGs never regenerated | TESTED | `test_T19_benchmark_and_illustrative_examples[5]` |
| T19 | Transparency statements present | TESTED | `test_T19_transparency_statements` |
| T20 | No API client loaded until Generate; no direct API imports in app_v2 / v2_recorded / v2_state | TESTED | `test_T20_app_loads_no_api_client_until_generate` (subprocess: litellm, openai, networkx, research module, dotenv all absent), `test_T20_no_direct_api_imports[3]` |
| T21 | App served over HTTP | TESTED (smoke) | `streamlit run app_v2.py --server.headless true --browser.gatherUsageStats false --server.address 127.0.0.1 --server.port 8767` without a key: health `ok`, `/` HTTP 200; stopped |

## Not verified / limitations
- Visual appearance in a real browser; the live path through a browser (the live UI check used AppTest).
- Live error paths with real litellm exceptions (only mocked); latency under poor network.
- Quality of generated decompositions in general (only 6 real decompositions were made; all looked structurally plausible,
  none was evaluated).
- Shared attempt/cost counter across concurrent sessions (D12).

## Repository check (Checkpoint 2)
- Protected files: `shasum -c repo_state/v2_protected_hashes_before.txt` 28/28 OK; research cache digest unchanged.
- Checkpoint 1 files: only `v2_state.py` changed (bug fix, D16); the other 7 frozen hashes match.
- See the final snapshot comparison in the report below this table (`repo_state/v2_cp2_after.txt`).
