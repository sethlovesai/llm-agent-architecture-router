import json
import os

import dag_width

CUSTOM = "__custom__"
HERE = os.path.dirname(os.path.abspath(__file__))
EXAMPLES_PATH = os.path.join(HERE, "data", "v1_examples.json")


def load_examples(path=EXAMPLES_PATH):
    with open(path) as f:
        return {e["key"]: e for e in json.load(f)["examples"]}


def init(state, examples, default=None):
    if "example" in state:
        return
    first = default or next(iter(examples))
    state["width_choice"] = None
    state["confirmed_width"] = None
    state["confirmed_text"] = None
    state["rec_requested"] = False
    state["edited_from"] = None
    select(state, examples, first)


def select(state, examples, key):
    """User picked an option in the example selector."""
    state["example"] = key
    state["width_choice"] = None
    state["confirmed_width"] = None
    state["confirmed_text"] = None
    state["edited_from"] = None
    if key == CUSTOM:
        state["task_text"] = ""
        state["source_example"] = None
        state["rec_requested"] = False
    else:
        state["task_text"] = examples[key]["description"]
        state["source_example"] = key


def edit_text(state, examples, new_text):
    """User changed the description text."""
    old_text = state.get("task_text", "")
    state["task_text"] = new_text
    if new_text == old_text:
        return
    src = state.get("source_example")
    if src is not None and new_text != examples[src]["description"]:
        # edited example text: drop the stored DAG association; it is now a custom task
        state["edited_from"] = src
        state["source_example"] = None
        state["example"] = CUSTOM
    # any text change invalidates a manual width confirmation and a pending recommendation for custom text
    if state.get("source_example") is None:
        state["width_choice"] = None
        state["confirmed_width"] = None
        state["confirmed_text"] = None
        state["rec_requested"] = False


def confirm_width(state):
    """Explicit confirmation of the manually chosen width (custom tasks only)."""
    if state.get("source_example") is not None:
        return False
    w = state.get("width_choice")
    if w is None:
        return False
    state["confirmed_width"] = int(w)
    state["confirmed_text"] = state.get("task_text", "")
    return True


def effective_width(state, examples):
    """(width, how) or (None, reason). Stored DAG for an unedited example; else a confirmed manual width."""
    src = state.get("source_example")
    if src is not None:
        ex = examples[src]
        if state.get("task_text") != ex["description"]:
            return None, "text no longer matches the example"   # defensive; edit_text normally handles this
        return dag_width.router_width(ex["subtasks"], ex["decomposition_warranted"]), "computed from stored DAG"
    if state.get("confirmed_width") is not None and state.get("confirmed_text") == state.get("task_text", ""):
        return state["confirmed_width"], "confirmed manually"
    return None, "width not confirmed"


def can_recommend(state, examples):
    return effective_width(state, examples)[0] is not None


def request_recommendation(state, examples):
    if not can_recommend(state, examples):
        return False
    state["rec_requested"] = True
    return True


def show_recommendation(state, examples):
    return bool(state.get("rec_requested")) and can_recommend(state, examples)
