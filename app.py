"""Recommendation-only prototype (v0) of the width-only Bayesian router.

Run:  cd prototype && .venv/bin/streamlit run app.py
"""
import numpy as np
import pandas as pd
import streamlit as st

import router_adapter as ra

st.set_page_config(page_title="Architecture router (v0)", layout="wide")


@st.cache_resource
def get_model():
    return ra.FrozenModel()


model = get_model()
evidence = ra.load_evidence()

st.title("Architecture recommendation (width-only Bayesian router, v0)")
st.caption(
    "Recommendation only. Based on a 24-task benchmark (CRMArena-Pro B2C subset, gpt-4o-mini, 3 repeats per task). "
    "Probabilities describe uncertainty in that benchmark evidence; they are not calibrated probabilities of success "
    "on other tasks. Nothing is executed: no architecture is run and no task is decomposed."
)

# ------------------------------------------------------------------ inputs
if "lam" not in st.session_state:
    st.session_state.lam = 0


def _set_lam(v):
    st.session_state.lam = v


col_in1, col_in2 = st.columns([1, 2])
with col_in1:
    width = st.number_input("DAG width (max subtasks that can run concurrently)", min_value=1, max_value=5, value=1, step=1,
                            key="width")
    st.caption(f"Widths with training data: {', '.join(str(w) for w in model.widths())}. "
               "Other widths use the router's empty-bucket fallback.")
with col_in2:
    st.slider("Cost weight lambda (quality points per USD per run)", min_value=0, max_value=300, key="lam")
    bcols = st.columns(4)
    for col, v in zip(bcols, (0, 10, 100, 300)):
        # on_click runs before the next script run, so it may set the slider's state
        col.button(f"lambda = {v}", key=f"btn_{v}", on_click=_set_lam, args=(v,))

lam = float(st.session_state.lam)
r = ra.recommend(model, int(width), lam)

# ------------------------------------------------------------------ recommendation
st.subheader(f"Recommended: {r['pick'].replace('_', '-')} ({ra.SHORT[r['pick']]})")
flags = []
if r["no_evidence"]:
    flags.append("NO EVIDENCE: no training task has this width. All three architectures get the Beta(1,1) prior and "
                 "the same fallback cost, so the pick is the router's deterministic tie-break (lower cost, then "
                 "single-agent, workflow, multi-agent).")
elif r["flag"] == "tie in estimate":
    flags.append("TIE: two or more architectures have exactly equal utility; the pick is the router's tie-break.")
if r["flag"] == "n=1 (cost SE unavailable)":
    flags.append("Only one category behind this bucket: cost standard error unavailable, so cost is held fixed in the simulation.")
if r["no_clear_winner"]:
    flags.append("NO CLEAR WINNER: the 95% credible interval for the utility gap includes zero. (Descriptive only; "
                 "it does not change the recommendation.)")
for f in flags:
    st.warning(f)

# ------------------------------------------------------------------ table
rows = []
for i, a in enumerate(ra.ARCHS):
    rows.append({
        "architecture": f"{a.replace('_', '-')} ({ra.SHORT[a]})",
        "recommended": "yes" if a == r["pick"] else "",
        "posterior mean quality ± SD": f"{r['mu'][i]:.4f} ± {r['sd'][i]:.4f}",
        "mean cost per run (USD)": f"{r['cost'][i]:.5f}",
        "utility (mu - lambda*cost)": f"{r['utility'][i]:.4f}",
        "P(best)": f"{r['P_best_each'][i]:.3f}",
    })
st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
st.markdown(
    f"**95% credible interval** for U(recommended) − U(best alternative): "
    f"**[{r['gap_lo']:+.4f}, {r['gap_hi']:+.4f}]**  ·  no clear winner: **{'yes' if r['no_clear_winner'] else 'no'}**  ·  "
    f"no evidence: **{'yes' if r['no_evidence'] else 'no'}**  ·  evidence flag: `{r['flag']}`"
)
st.caption(f"P(best) = share of {ra.DRAWS:,} Monte Carlo draws (fixed seed {ra.SEED}, stream key {ra.DEFAULT_SEED_KEY}) in which "
           "that architecture has the highest utility. Quality ~ Beta posterior; cost ~ Normal(mean, SE) clipped at 0 "
           "(held fixed when the SE is unavailable).")

# ------------------------------------------------------------------ evidence
st.subheader("Evidence behind this bucket")
ev = evidence.get(int(width))
if ev is None:
    st.write(f"Width {int(width)}: no training tasks (empty bucket).")
else:
    st.write(f"Width {int(width)}: **{r['n_categories']}** categories (the Beta evidence units) from "
             f"**{ev['n_tasks']}** tasks: {', '.join(str(t) for t in ev['task_ids'])}.")
    with st.expander("Categories"):
        st.write(", ".join(ev["categories"]))
st.caption("Model: frozen copy of results/router_dist/bucket_model.json (fitted on all 24 tasks); soft-count Beta update, "
           "posterior Beta(1+s, 1+n-s), mean (1+s)/(2+n), SD sqrt(mu(1-mu)/(n+3)). See README.md and DECISIONS.md.")
