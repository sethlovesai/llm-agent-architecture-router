import os

import pandas as pd
import streamlit as st

import dag_width
import live_decompose as ld
import router_adapter as ra
import v1_explain
import v1_state as vs
import v2_recorded as rec
import v2_state as v2

st.set_page_config(page_title="CRM architecture recommender (v2)", layout="wide")

NAMES = v1_explain.NAMES
LAM_QUICK = (0, 10, 100, 300)


@st.cache_resource
def _model():
    return ra.FrozenModel()


@st.cache_data
def _examples():
    return vs.load_examples()


@st.cache_data
def _recorded():
    return rec.load_recorded()


model = _model()
examples = _examples()
recorded = _recorded()
evidence = ra.load_evidence()
S = st.session_state


def _sync():
    S["example_select"] = S["example"]
    S["task_text_input"] = S["task_text"]
    S["context_input"] = S.get("context_text", "")


if "example" not in S:
    v2.init(S, examples)
    S["recorded_example"] = None
    S["v2_error"] = None
    _sync()
if "lam" not in S:
    S["lam"] = 0


# ------------------------------------------------------------------ callbacks
def _on_select():
    key = S["example_select"]
    S["v2_error"] = None
    if rec.is_recorded(key):
        rec.select(S, examples, recorded[key])
    else:
        v2.select(S, examples, key)
        S["recorded_example"] = None
    _sync()


def _on_text():
    v2.edit_text(S, examples, S["task_text_input"])
    S["recorded_example"] = None
    S["v2_error"] = None
    _sync()


def _on_context():
    v2.edit_context(S, S["context_input"])
    if S.get("source_example") is None:
        S["recorded_example"] = None
        S["example"] = vs.CUSTOM
    S["v2_error"] = None
    _sync()


def _on_generate():
    S["v2_error"] = None
    try:
        g = ld.generate(S.get("task_text", ""), S.get("context_text", ""))
    except ld.GenerationError as e:
        S["v2_error"] = e.user_message
        return
    except ld.DecomposerUnavailable as e:
        S["v2_error"] = str(e)
        return
    if not v2.record_generation(S, g):
        S["v2_error"] = "The task text changed while generating; please generate again."


def _on_confirm_generated():
    v2.confirm_generated(S)


def _on_override():
    v2.confirm_override(S, S.get("override_choice"))


def _on_confirm_manual():
    vs.confirm_width(S)


def _on_recommend():
    v2.request_recommendation(S, examples)


def _set_lam(v):
    S["lam"] = v


def _label(k):
    if k == vs.CUSTOM:
        return "Custom task (describe your own)"
    if rec.is_recorded(k):
        return f"{recorded[k]['label']}  [{rec.LABEL}]"
    ex = examples[k]
    origin = "Benchmark example — in sample" if ex["origin"] == "benchmark_in_sample" else "Illustrative example"
    return f"{ex['label']}  [{origin}]"


def _dag_table(subtasks):
    st.dataframe(pd.DataFrame([{"subtask": s["id"], "role": s["role"], "description": s["description"],
                                "depends on": ", ".join(s["depends_on"]) or "—"} for s in subtasks]),
                 hide_index=True, width="stretch")


# ------------------------------------------------------------------ header
st.title("Which agent architecture fits this CRM task?")
st.caption("Research prototype (v2). Describe a CRM task, let the research decomposition prompt turn it into a "
           "subtask graph (DAG), confirm its width, and get a Single-Agent / Workflow / Multi-Agent recommendation "
           "from the width-only Bayesian router. It recommends only: it never executes an architecture or touches a CRM.")
with st.expander("How this works"):
    st.markdown("**CRM task → LLM decomposition (research prompt, gpt-4o-mini, temperature 0) → DAG width → your "
                "confirmation → Bayesian router → recommendation.** Width = the largest number of subtasks with no "
                "dependency between them. The router uses only the confirmed width and your cost preference; the "
                "text itself never enters the router.")

# ------------------------------------------------------------------ 1. describe
st.header("1. Describe your CRM task")
options = list(examples) + list(recorded) + [vs.CUSTOM]
st.selectbox("Start from an example, a recorded generated example, or a custom task", options, format_func=_label,
             key="example_select", on_change=_on_select)
st.text_area("CRM task description", key="task_text_input", height=100, on_change=_on_text,
             placeholder="e.g. Find customers with an open complaint and a renewal due in 60 days, and draft a retention note.")
src = S.get("source_example")
if src is None:
    st.text_area("Optional context (sent to the decomposer together with the task)", key="context_input", height=70,
                 on_change=_on_context, placeholder="e.g. 'recent' means the last 90 days; our CRM is Salesforce.")
if src is not None:
    ex = examples[src]
    if ex["origin"] == "benchmark_in_sample":
        st.info(f"**Benchmark example — in sample.** Task {ex['task_id']} ({ex['category']}) is one of the 24 tasks the "
                "router was fitted on; its DAG is the stored research decomposition.")
    else:
        st.info("**Illustrative example.** Hand-written DAG to demonstrate the interface; not evaluated evidence.")
elif S.get("recorded_example"):
    st.info(f"**{rec.LABEL}.** Generated earlier with the same live decomposition used below (stored so the demo "
            "works without an API key). It is not part of the benchmark and was not evaluated.")
elif S.get("edited_from"):
    st.warning(f"You edited the text of the example \"{examples[S['edited_from']]['label']}\". It is now a custom task; "
               "the stored DAG no longer applies.")

# ------------------------------------------------------------------ 2. structure
st.header("2. Task structure (DAG)")
st.caption("DAG width is the maximum number of independent subtasks that can run at the same time.")
if src is not None:
    ex = examples[src]
    w_auto = dag_width.router_width(ex["subtasks"], ex["decomposition_warranted"])
    st.metric("DAG width (computed from the stored DAG)", w_auto)
    _dag_table(ex["subtasks"])
else:
    key_present = bool(os.environ.get("OPENAI_API_KEY"))
    gen = v2.current_generation(S)
    c1, c2 = st.columns(2)
    label = "Regenerate DAG" if gen else "Generate DAG with LLM"
    c1.button(label, key="generate", type="primary" if not gen else "secondary", on_click=_on_generate,
              disabled=not key_present or not (S.get("task_text") or "").strip())
    if not key_present:
        c2.info("Live decomposition is unavailable: no OPENAI_API_KEY in the environment. Use an example, a recorded "
                "generated example, or set the width manually below.")
    if S.get("v2_error"):
        st.error(S["v2_error"])
    if gen:
        st.metric("DAG width (computed from the generated DAG)", gen["width"])
        st.caption(f"Width check: research calculation = {gen['width_checks']['research_compute_features']}, prototype "
                   f"calculation = {gen['width_checks']['prototype_dag_width']} (agree). {ld.WIDTH_CHECK_MEANING}")
        if gen["decomposition_warranted"]:
            size, members = dag_width.max_antichain_width(gen["subtasks"])
            st.write(f"Largest set of independent subtasks: {', '.join(members)}. Longest dependency chain: {gen['depth']} steps.")
        else:
            st.write("The decomposer judged this a single-step task (not decomposed), so its width is 1.")
        _dag_table(gen["subtasks"])
        st.warning(f"**{ld.PROVENANCE_LABEL}.** Check that the subtasks make sense before relying on the width. "
                   + " ".join(gen["notes"]))
        hist = [h["width"] for h in S.get("v2_history", [])]
        if v2.width_changed_across_regenerations(S):
            st.error(f"The width changed between generations ({' → '.join(map(str, hist))}): the decomposition of this task "
                     "is not stable, so treat the width (and the recommendation) with extra caution.")
        elif len(hist) > 1:
            st.success(f"Same width in all {len(hist)} generations ({hist[0]}).")
        with st.expander("Generation details"):
            st.markdown(f"- Model `{gen['model']}`, temperature {gen['temperature']}, attempts {gen['attempts']} of "
                        f"{gen['max_retries']}, cost {('$%.5f' % gen['cost_usd']) if gen['cost_usd'] is not None else 'n/a'}, "
                        f"generated {gen['timestamp_utc']}.\n"
                        f"- Research decomposer `decomposition/decompose.py` @ `{gen['decompose_commit']}` "
                        f"(sha256 `{gen['decompose_sha256'][:16]}…`); prompt and validation reused unchanged.\n"
                        f"- Context included: {'yes' if gen['context_included'] else 'no'}.")
        b1, b2 = st.columns(2)
        b1.button(f"Use generated width ({gen['width']})", key="confirm_generated", on_click=_on_confirm_generated)
        b2.selectbox("…or correct the width manually", [1, 2, 3, 4, 5], index=None, key="override_choice",
                     placeholder="Select a width…")
        b2.button("Use this width instead", key="confirm_override", on_click=_on_override,
                  disabled=S.get("override_choice") is None)
    else:
        with st.expander("Or set the width manually (no decomposition)", expanded=not key_present):
            st.caption("Your text is not analysed when you set the width manually.")
            st.selectbox("DAG width (1-5)", [1, 2, 3, 4, 5], index=None, key="width_choice", placeholder="Select a width…")
            st.button("Confirm width", key="confirm_width", on_click=_on_confirm_manual,
                      disabled=S.get("width_choice") is None)

w_eff, how = v2.effective_width(S, examples)
if src is None:
    if w_eff is None:
        st.write("Width: **not confirmed yet**.")
    else:
        st.success(f"Width {w_eff} — {how}.")

# ------------------------------------------------------------------ 3. recommendation
st.header("3. Architecture recommendation")
st.slider("Cost preference lambda (0 = quality only; higher = cheaper architectures favoured)", 0, 300, key="lam")
for col, v in zip(st.columns(len(LAM_QUICK)), LAM_QUICK):
    col.button(f"lambda = {v}", key=f"lam_{v}", on_click=_set_lam, args=(v,))
st.button("Get recommendation", key="recommend", type="primary", on_click=_on_recommend, disabled=w_eff is None)
if w_eff is None:
    st.caption("Confirm a width in step 2 to enable the recommendation.")

if v2.show_recommendation(S, examples):
    lam = float(S["lam"])
    r = ra.recommend(model, int(w_eff), lam)
    st.subheader(f"Recommended architecture: {NAMES[r['pick']]} ({ra.SHORT[r['pick']]})")
    st.write(v1_explain.explain(r))
    if r["no_evidence"]:
        st.error("No evidence: no benchmark task has this width. The pick is a fixed tie-break default, not a "
                 "data-based recommendation.")
    if r["no_clear_winner"]:
        st.warning("No clear winner: the 95% credible interval for the recommendation's utility advantage includes zero.")
    if r["n_categories"] == 1:
        st.warning("Limited evidence: only one task category has this width. A chance of being best close to 100% "
                   "here does not mean reliable real-world superiority.")
    if how.startswith("generated") or how.startswith("manual override"):
        st.caption(f"Width source: {how}. The recommendation is only as reliable as this width.")
    rows = []
    for i, a in enumerate(ra.ARCHS):
        rows.append({"architecture": f"{NAMES[a]} ({ra.SHORT[a]})", "recommended": "★" if a == r["pick"] else "",
                     "Estimated quality (mean ± SD)": f"{r['mu'][i]:.3f} ± {r['sd'][i]:.3f}",
                     "Estimated cost (USD per run)": f"{r['cost'][i]:.5f}",
                     "Expected utility": f"{r['utility'][i]:.4f}",
                     "Chance of being best within this model": f"{r['P_best_each'][i]*100:.1f}%"})
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    st.write(f"Utility advantage of {NAMES[r['pick']]} over the best alternative, 95% credible interval: "
             f"**[{r['gap_lo']:+.3f}, {r['gap_hi']:+.3f}]**")
    ev = evidence.get(int(w_eff))
    st.markdown(f"**Strength of supporting evidence:** width {int(w_eff)}; {ev['n_tasks'] if ev else 0} historical "
                f"benchmark tasks from {r['n_categories']} distinct categories.")
    with st.expander("Technical details"):
        st.markdown(
            f"- Model: frozen `data/bucket_model.json` (width-only soft-count Beta model, 24 tasks). Posterior Beta(1+s, "
            f"1+n−s); mean (1+s)/(2+n); SD √(mean(1−mean)/(n+3)).\n"
            f"- Utility = mean − lambda × cost (USD per run); exact ties go to the lower cost, then SA, WF, MA.\n"
            f"- Chance of being best: {ra.DRAWS:,} Monte Carlo draws (seed {ra.SEED}, stream key {ra.DEFAULT_SEED_KEY}).\n"
            f"- Evidence flag: `{r['flag']}`. Historical task ids at this width: "
            f"{', '.join(map(str, ev['task_ids'])) if ev else 'none'}.")

st.divider()
st.caption("Important: (1) generated DAGs come from an LLM and are not evaluated — check them before trusting the width; "
           "(2) the prototype recommends but never executes an architecture; (3) benchmark examples are in-sample, and "
           "illustrative and recorded examples are not benchmark evidence; (4) the chance of being best is a model-based "
           "estimate, not a guarantee of success; (5) in the project's evaluation the width-only router did not "
           "outperform the best fixed strategy; (6) widths 2 and 4 rest on very few task categories, and widths 3 and "
           "5+ have no evidence.")
