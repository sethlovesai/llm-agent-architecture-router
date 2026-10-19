"""v1: CRM task input -> stored DAG / manual width -> width-only Bayesian router (recommendation only).

Run:  cd prototype && .venv/bin/streamlit run app_v1.py
The router part reuses router_adapter.py and data/bucket_model.json from v0 unchanged.
"""
import pandas as pd
import streamlit as st

import dag_width
import router_adapter as ra
import v1_explain
import v1_state as vs

st.set_page_config(page_title="CRM architecture recommender (v1)", layout="wide")

NAMES = v1_explain.NAMES
LAM_QUICK = (0, 10, 100, 300)


@st.cache_resource
def _model():
    return ra.FrozenModel()


@st.cache_data
def _examples():
    return vs.load_examples()


model = _model()
examples = _examples()
evidence = ra.load_evidence()
S = st.session_state


def _sync_widgets():
    S["example_select"] = S["example"]
    S["task_text_input"] = S["task_text"]


if "example" not in S:
    vs.init(S, examples)
    _sync_widgets()
if "lam" not in S:
    S["lam"] = 0


# ------------------------------------------------------------------ callbacks (run before the next script pass)
def _on_select():
    vs.select(S, examples, S["example_select"])
    _sync_widgets()


def _on_text():
    vs.edit_text(S, examples, S["task_text_input"])
    _sync_widgets()


def _on_confirm():
    vs.confirm_width(S)


def _on_recommend():
    vs.request_recommendation(S, examples)


def _set_lam(v):
    S["lam"] = v


def _origin_label(ex):
    return ("Benchmark example — in sample" if ex["origin"] == "benchmark_in_sample" else "Illustrative example")


# ------------------------------------------------------------------ header
st.title("Which agent architecture fits this CRM task?")
st.caption("Recommendation-only research prototype (v1). It recommends Single-Agent, Workflow or Multi-Agent from a "
           "task's DAG width and your cost preference. It does not execute any architecture, does not call any model "
           "or API, and does not analyse or decompose free text.")
with st.expander("How this works (pipeline)"):
    st.markdown("**CRM task → task decomposition → DAG width → Bayesian router → architecture recommendation.**  \n"
                "For the predefined examples the decomposition is a *stored* DAG (benchmark examples: the cached DAG used "
                "in the project's evaluation). For a custom task there is no automatic decomposition: you choose the width.")

# ------------------------------------------------------------------ 1. describe
st.header("1. Describe your CRM task")
options = list(examples) + [vs.CUSTOM]
fmt = lambda k: "Custom task" if k == vs.CUSTOM else f"{examples[k]['label']}  [{_origin_label(examples[k])}]"
st.selectbox("Start from an example, or choose Custom task", options, format_func=fmt, key="example_select",
             on_change=_on_select)
st.text_area("CRM task description", key="task_text_input", height=110, on_change=_on_text,
             placeholder="Describe the CRM task (for a custom task this text is shown back to you but not analysed).")

src = S.get("source_example")
if src is not None:
    ex = examples[src]
    if ex["origin"] == "benchmark_in_sample":
        st.info(f"**Benchmark example — in sample.** Task {ex['task_id']} ({ex['category']}) is one of the 24 tasks the "
                "router was fitted on, so it is not unseen validation data.")
    else:
        st.info("**Illustrative example.** Authored to demonstrate the interface; its DAG is hand-written and it is "
                "not part of the evaluated benchmark evidence.")
elif S.get("edited_from"):
    st.warning(f"You edited the text of the example \"{examples[S['edited_from']]['label']}\". It is now treated as a "
               "custom task: the example's stored DAG no longer applies and you must confirm a width.")

# ------------------------------------------------------------------ 2. structure
st.header("2. Review task structure")
st.caption("DAG width is the maximum number of independent subtasks that can run at the same time.")
if src is not None:
    ex = examples[src]
    w_auto = dag_width.router_width(ex["subtasks"], ex["decomposition_warranted"])
    c1, c2 = st.columns([1, 3])
    c1.metric("DAG width (computed from the stored DAG)", w_auto)
    if not ex["decomposition_warranted"]:
        c2.write("This task was not decomposed (a single step), so its width is 1.")
    else:
        size, members = dag_width.max_antichain_width(ex["subtasks"])
        c2.write(f"Largest set of subtasks with no dependency between them: {', '.join(members)} "
                 f"({size} subtask{'s' if size != 1 else ''}). Longest dependency chain: {dag_width.depth(ex['subtasks'])} steps.")
    st.dataframe(pd.DataFrame([{"subtask": s["id"], "role": s["role"], "description": s["description"],
                                "depends on": ", ".join(s["depends_on"]) or "—"} for s in ex["subtasks"]]),
                 hide_index=True, width="stretch")
    with st.expander("Source of this DAG"):
        st.write(f"Source: `{ex['source']}`" + (f"  (sha256 `{ex['source_sha256'][:16]}…`)" if ex["source_sha256"] else ""))
        st.write("Width is recomputed in the app from the subtasks' dependencies (largest antichain of the dependency "
                 "graph, all subtasks counted), following decomposition/decompose.py's definition.")
else:
    st.warning("Automatic task decomposition is not available. Your text is not analysed by the router.")
    st.selectbox("Choose the DAG width for this task (1-5)", [1, 2, 3, 4, 5], index=None, key="width_choice",
                 placeholder="Select a width…")
    st.button("Confirm width", key="confirm_width", on_click=_on_confirm, disabled=S.get("width_choice") is None)
    w_eff, how = vs.effective_width(S, examples)
    if w_eff is None:
        st.write("Width: **not confirmed yet**.")
    else:
        st.success(f"Width {w_eff} confirmed for this task text.")

# ------------------------------------------------------------------ 3. recommendation
st.header("3. Architecture recommendation")
w_eff, how = vs.effective_width(S, examples)
st.slider("Cost preference lambda (0 = quality only; higher = cheaper architectures favoured)", 0, 300, key="lam")
qcols = st.columns(len(LAM_QUICK))
for col, v in zip(qcols, LAM_QUICK):
    col.button(f"lambda = {v}", key=f"lam_{v}", on_click=_set_lam, args=(v,))
st.button("Get recommendation", key="recommend", type="primary", on_click=_on_recommend, disabled=w_eff is None)
if w_eff is None:
    st.caption("Confirm a width in step 2 to enable the recommendation.")

if vs.show_recommendation(S, examples):
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
        st.warning("Limited evidence: only one task category has this width (width 4 in this benchmark). A chance of "
                   "being best close to 100% here does not mean reliable real-world superiority.")
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
    strength = ("none" if r["n_categories"] == 0 else "very limited (1 category)" if r["n_categories"] == 1
                else "limited (2 categories)" if r["n_categories"] == 2 else f"{r['n_categories']} categories")
    st.markdown(f"**Strength of supporting evidence:** width {int(w_eff)} ({how}); "
                f"{ev['n_tasks'] if ev else 0} historical benchmark tasks from {r['n_categories']} distinct categories "
                f"— {strength}.")
    with st.expander("Technical details"):
        st.markdown(
            f"- Model: frozen `data/bucket_model.json` (width-only soft-count Beta model fitted on all 24 tasks). Posterior "
            f"Beta(1+s, 1+n−s); mean (1+s)/(2+n); SD √(mean(1−mean)/(n+3)); this is a soft-count update, not an exact "
            f"binomial likelihood.\n"
            f"- Utility = mean − lambda × cost (USD per run). Exact ties (<1e-9) go to the lower cost, then SA, WF, MA.\n"
            f"- Chance of being best: share of {ra.DRAWS:,} Monte Carlo draws (seed {ra.SEED}, stream key "
            f"{ra.DEFAULT_SEED_KEY}); quality ~ Beta posterior, cost ~ Normal(mean, SE) clipped at 0 (fixed when no SE).\n"
            f"- Evidence flag: `{r['flag']}`. Historical task ids at this width: "
            f"{', '.join(map(str, ev['task_ids'])) if ev else 'none'}.")

st.divider()
st.caption("Important: (1) custom task text is not analysed or decomposed; (2) the prototype recommends but never executes "
           "an architecture; (3) benchmark examples are in-sample and illustrative examples are not evaluated evidence; "
           "(4) the chance of being best is a model-based estimate, not a guarantee of success; (5) in the project's "
           "evaluation the width-only router did not outperform the best fixed strategy; (6) width 4 has very limited "
           "evidence, so a chance of being best near 100% there does not imply reliable superiority.")
