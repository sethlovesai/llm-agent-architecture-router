import live_decompose as ld
import v1_state as vs

CUSTOM = vs.CUSTOM


def init(state, examples, default=None):
    first_time = "example" not in state
    vs.init(state, examples, default)
    if first_time or "context_text" not in state:
        state["context_text"] = ""
        state["v2_generations"] = {}
        _clear_generation(state)


def _clear_generation(state):
    state["v2_history"] = []
    state["v2_current"] = None
    state["v2_confirmed"] = None


def current_hash(state):
    return ld.input_hash(state.get("task_text", ""), state.get("context_text", ""))


def select(state, examples, key):
    vs.select(state, examples, key)
    state["context_text"] = ""
    _clear_generation(state)


def edit_text(state, examples, new_text):
    old = state.get("task_text", "")
    vs.edit_text(state, examples, new_text)
    if new_text != old:
        _clear_generation(state)   # vs.edit_text already cleared manual confirmation and the request for custom text


def edit_context(state, new_context):
    if (new_context or "") == (state.get("context_text") or ""):
        return
    state["context_text"] = new_context or ""
    if state.get("source_example") is None:
        _clear_generation(state)
        state["width_choice"] = None
        state["confirmed_width"] = None
        state["confirmed_text"] = None
        state["rec_requested"] = False


def record_generation(state, gen):
    """Attach a successful Generation to the current custom input. Returns False if it does not belong to it."""
    if state.get("source_example") is not None:
        return False
    d = gen.to_dict() if hasattr(gen, "to_dict") else dict(gen)   # Generation object or a stored generation dict
    if d["input_hash"] != current_hash(state):
        return False
    state["v2_generations"][d["input_hash"]] = d
    if state.get("v2_current") != d["input_hash"]:
        state["v2_history"] = []
    state["v2_current"] = d["input_hash"]
    state["v2_history"].append({"input_hash": d["input_hash"], "width": d["width"], "timestamp_utc": d["timestamp_utc"]})
    state["v2_confirmed"] = None          # a (re)generation always needs a fresh confirmation
    state["rec_requested"] = False
    return True


def current_generation(state):
    h = state.get("v2_current")
    if h is None or h != current_hash(state) or state.get("source_example") is not None:
        return None
    return state["v2_generations"].get(h)


def width_changed_across_regenerations(state):
    return len({x["width"] for x in state.get("v2_history", [])}) > 1


def confirm_generated(state):
    g = current_generation(state)
    if g is None:
        return False
    state["v2_confirmed"] = {"width": int(g["width"]), "source": "generated", "input_hash": g["input_hash"],
                             "generated_width": int(g["width"])}
    return True


def confirm_override(state, width):
    """Manual correction of a generated width (explicit action)."""
    g = current_generation(state)
    if g is None or width is None:
        return False
    state["v2_confirmed"] = {"width": int(width), "source": "manual override", "input_hash": g["input_hash"],
                             "generated_width": int(g["width"])}
    return True


def effective_width(state, examples):
    """(width, how) or (None, reason)."""
    if state.get("source_example") is not None:
        return vs.effective_width(state, examples)
    c = state.get("v2_confirmed")
    if c is not None and c["input_hash"] == current_hash(state) and current_generation(state) is not None:
        if c["source"] == "generated":
            return c["width"], "generated DAG (confirmed)"
        diff = "" if c["width"] == c["generated_width"] else f"; differs from generated width {c['generated_width']}"
        return c["width"], f"manual override (confirmed{diff})"
    # v1 manual path (no generation needed); edit_text / edit_context clear its confirmation
    return vs.effective_width(state, examples)


def can_recommend(state, examples):
    return effective_width(state, examples)[0] is not None


def request_recommendation(state, examples):
    if not can_recommend(state, examples):
        return False
    state["rec_requested"] = True
    return True


def show_recommendation(state, examples):
    return bool(state.get("rec_requested")) and can_recommend(state, examples)
