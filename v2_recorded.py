import json
import os

import dag_width
import v2_state as v2

HERE = os.path.dirname(os.path.abspath(__file__))
RECORDED_PATH = os.path.join(HERE, "data", "v2_recorded_examples.json")
PREFIX = "rec_"
LABEL = "Recorded LLM-generated example — not evaluated"


def load_recorded(path=RECORDED_PATH):
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        return {e["key"]: e for e in json.load(f)["examples"]}


def is_recorded(key):
    return isinstance(key, str) and key.startswith(PREFIX)


def check(entry):
    """Recompute the width of a recorded DAG; returns (ok, width)."""
    g = entry["generation"]
    w = dag_width.router_width(g["subtasks"], g["decomposition_warranted"])
    return w == g["width"] == g["width_checks"]["prototype_dag_width"] == g["width_checks"]["research_compute_features"], w


def select(state, examples, entry):
    """Load a recorded example into the custom path with its stored generation attached."""
    v2.select(state, examples, v2.CUSTOM)
    g = entry["generation"]
    state["task_text"] = g["task_text"]
    state["context_text"] = g["context_text"]
    state["width_choice"] = None
    state["confirmed_width"] = None
    state["confirmed_text"] = None
    ok = v2.record_generation(state, g)
    state["example"] = entry["key"]
    state["recorded_example"] = entry["key"]
    return ok
