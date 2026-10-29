import numpy as np

NAMES = {"single_agent": "Single-Agent", "workflow": "Workflow", "multi_agent": "Multi-Agent"}


def explain(r):
    pick = NAMES[r["pick"]]
    w, lam = r["width"], r["lambda"]
    if r["no_evidence"]:
        return (f"No historical benchmark task has width {w}, so the model has no evidence for this width. All three "
                f"architectures get the same uninformed estimate and the same fallback cost; {pick} is shown only because "
                f"of the router's fixed tie-break rule (lower cost, then Single-Agent, Workflow, Multi-Agent). "
                f"Treat this as 'no recommendation available'.")
    parts = []
    pref = "quality only (cost ignored)" if lam == 0 else f"this cost preference (lambda = {lam:g})"
    parts.append(f"{pick} has the highest expected utility for width {w} and {pref}.")
    best_q = int(np.argmax(r["mu"]))
    pi = ["single_agent", "workflow", "multi_agent"].index(r["pick"])
    if best_q != pi and r["mu"][best_q] > r["mu"][pi]:
        parts.append(f"{NAMES[['single_agent', 'workflow', 'multi_agent'][best_q]]} has a higher estimated quality, but "
                     f"{pick}'s lower estimated cost gives it the higher utility at this cost weight.")
    if r["flag"] == "tie in estimate":
        parts.append("Two or more architectures have exactly equal utility; the pick comes from the router's tie-break rule.")
    if r["no_clear_winner"]:
        parts.append("However, the available evidence does not establish a clear winner: the 95% interval for its "
                     "utility advantage includes zero.")
    else:
        parts.append("Within this model the 95% interval for its utility advantage excludes zero.")
    if r["n_categories"] == 1:
        parts.append("This width is supported by a single task category, so its cost uncertainty is not estimated; a "
                     "high chance of being best here does not imply reliable real-world superiority.")
    return " ".join(parts)
