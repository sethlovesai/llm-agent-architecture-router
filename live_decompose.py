import datetime
import hashlib
import importlib.util
import json
import os
import re
import sys
from dataclasses import asdict, dataclass, field

import dag_width

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
DECOMPOSE_PATH = os.path.join(HERE, "research", "decompose.py")
PINNED_SHA256 = "4bcf6602accbab788cbf2916e45e8dc3fa7f4539c99f8b06228c058ae80c455b"
PINNED_COMMIT = "1e7e83b"

MAX_TASK_CHARS = 2000
MAX_CONTEXT_CHARS = 2000
REQUEST_TIMEOUT_S = 60
TEMPERATURE = 0.0          # decompose_task's default, used for all 24 cached DAGs
MAX_RETRIES = 3            # decompose_task's default
CONTEXT_HEADER = "Additional context provided by the user:"

PROVENANCE_LABEL = "LLM-generated, not evaluated"
WIDTH_CHECK_MEANING = ("Two independent width calculations agree on this DAG. This confirms the width is computed "
                       "consistently for this DAG; it does not show that the LLM's decomposition is correct.")
PRIVACY_NOTE = ("Custom tasks have no benchmark category, so the research code's category-based privacy refusal-check "
                "injection is not applied.")
CONTEXT_NOTE = ("Context included: the decomposer received the task text plus user-supplied context. The research "
                "decompositions used the task text only, so this input differs from the research setting.")


class DecomposerUnavailable(Exception):
    """The live decomposer cannot be used at all (research file changed, import failed)."""


class GenerationError(Exception):
    """One generation failed. `kind` in {input, missing_key, timeout, auth, api_error, invalid_output, width_mismatch}."""

    def __init__(self, kind, user_message):
        super().__init__(user_message)
        self.kind = kind
        self.user_message = user_message


@dataclass
class Generation:
    input_hash: str
    task_text: str
    context_text: str
    context_included: bool
    composed_query: str
    decomposition_warranted: bool
    subtasks: list
    features: object
    width: int
    width_checks: dict
    depth: int
    model: str
    temperature: float
    max_retries: int
    attempts: int
    cost_usd: object
    timestamp_utc: str
    decompose_sha256: str
    decompose_commit: str
    provenance: str = PROVENANCE_LABEL
    notes: list = field(default_factory=list)

    def to_dict(self):
        return asdict(self)


# ------------------------------------------------------------------------------ input
def compose_query(task_text, context_text=""):
    """The single string passed as decompose's `query`. Without context it is exactly the task text
    (the research setting); with context, the task text, a blank line, a header line and the context."""
    task = (task_text or "").strip()
    ctx = (context_text or "").strip()
    if not ctx:
        return task, False
    return f"{task}\n\n{CONTEXT_HEADER}\n{ctx}", True


def input_hash(task_text, context_text=""):
    return hashlib.sha256(compose_query(task_text, context_text)[0].encode("utf-8")).hexdigest()


def _validate_input(task_text, context_text):
    task = (task_text or "").strip()
    if not task:
        raise GenerationError("input", "Please enter a task description before generating a decomposition.")
    if len(task) > MAX_TASK_CHARS:
        raise GenerationError("input", f"The task description is longer than {MAX_TASK_CHARS} characters.")
    if len((context_text or "").strip()) > MAX_CONTEXT_CHARS:
        raise GenerationError("input", f"The additional context is longer than {MAX_CONTEXT_CHARS} characters.")


# ------------------------------------------------------------------------------ research module
def sha256_of(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


class CompletionSeam:
    """Replaces `completion` inside the imported research module (in memory only; the file is untouched).
    Counts attempts, records per-call cost, adds a request timeout. Tests swap `backend` for a fake."""

    def __init__(self, backend):
        self.backend = backend
        self.calls = []

    def reset(self):
        self.calls = []

    def __call__(self, **kwargs):
        kwargs.setdefault("timeout", REQUEST_TIMEOUT_S)
        res = self.backend(**kwargs)
        cost = None
        hp = getattr(res, "_hidden_params", None)
        if isinstance(hp, dict):
            cost = hp.get("response_cost")
        self.calls.append({"kwargs": {k: v for k, v in kwargs.items() if k != "api_key"}, "cost": cost})
        return res


_MODULE = None
_SEAM = None


def load_decomposer(expected_sha256=None):
    """Imports decomposition/decompose.py (once) with the safety measures above. Raises DecomposerUnavailable.
    The pin is re-checked on every call, so a changed research file disables the live path immediately."""
    global _MODULE, _SEAM
    expected_sha256 = expected_sha256 or PINNED_SHA256
    if _MODULE is not None:
        if sha256_of(DECOMPOSE_PATH) != expected_sha256:
            raise DecomposerUnavailable("decomposition/decompose.py has changed since it was pinned; live decomposition is disabled.")
        return _MODULE, _SEAM
    if not os.path.exists(DECOMPOSE_PATH):
        raise DecomposerUnavailable("decomposition/decompose.py not found; live decomposition is disabled.")
    actual = sha256_of(DECOMPOSE_PATH)
    if actual != expected_sha256:
        raise DecomposerUnavailable("decomposition/decompose.py has changed since it was pinned "
                                    f"(expected sha256 {expected_sha256[:12]}…, found {actual[:12]}…); live decomposition is disabled.")
    os.environ["LITELLM_MODE"] = "PRODUCTION"
    os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"
    prev = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec = importlib.util.spec_from_file_location("research_decompose", DECOMPOSE_PATH)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    except Exception as e:  # missing packages etc.
        raise DecomposerUnavailable(f"Could not import the research decomposer ({type(e).__name__}).") from None
    finally:
        sys.dont_write_bytecode = prev
    try:
        import litellm
        litellm.telemetry = False
    except Exception:
        pass
    _SEAM = CompletionSeam(mod.completion)
    mod.completion = _SEAM
    _MODULE = mod
    return _MODULE, _SEAM


def system_prompt():
    mod, _ = load_decomposer()
    return mod.SYSTEM_PROMPT


# ------------------------------------------------------------------------------ generation
_KEY_RE = re.compile(r"(sk-[A-Za-z0-9_\-]{4})[A-Za-z0-9_\-\*]+")


def _safe(msg):
    return _KEY_RE.sub(r"\1…", str(msg))[:300]


def _classify(e):
    name = type(e).__name__.lower()
    text = str(e).lower()
    if "timeout" in name or "timed out" in text:
        return GenerationError("timeout", "The decomposition request timed out. Try again, or set the width manually.")
    if "authentication" in name or "auth" in name or "api key" in text:
        return GenerationError("auth", "The API rejected the request (authentication). Check that OPENAI_API_KEY is valid.")
    return GenerationError("api_error", f"The decomposition request failed ({type(e).__name__}: {_safe(e)}). "
                                        "Try again, or set the width manually.")


def generate(task_text, context_text=""):
    """One live decomposition. Returns a Generation; raises GenerationError / DecomposerUnavailable.
    Writes no files and stores nothing outside the returned object."""
    _validate_input(task_text, context_text)
    if not os.environ.get("OPENAI_API_KEY"):
        raise GenerationError("missing_key", "Live decomposition needs OPENAI_API_KEY in the environment. "
                                             "You can still use the examples or set the width manually.")
    mod, seam = load_decomposer()
    query, ctx_included = compose_query(task_text, context_text)
    seam.reset()
    try:
        data, graph = mod._decompose_with_retries(query, model=mod.DEFAULT_MODEL, temperature=TEMPERATURE,
                                                  max_retries=MAX_RETRIES)
    except mod.DecompositionError as e:
        raise GenerationError("invalid_output", "The LLM did not produce a valid DAG after "
                                                f"{MAX_RETRIES} attempts ({_safe(e)}). Try Regenerate, or set the width manually.") from None
    except GenerationError:
        raise
    except Exception as e:
        raise _classify(e) from None
    subtasks = data["subtasks"]
    warranted = bool(data["decomposition_warranted"])
    features = mod.compute_features(graph) if warranted else None
    w_research = features["parallelism_width"] if warranted else 1     # router rule for an undecomposed task
    w_proto = dag_width.router_width(subtasks, warranted)
    if w_research != w_proto:
        raise GenerationError("width_mismatch", f"The two width calculations disagree ({w_research} vs {w_proto}); "
                                                "the result was rejected.")
    costs = [c["cost"] for c in seam.calls if c["cost"] is not None]
    notes = [PRIVACY_NOTE] + ([CONTEXT_NOTE] if ctx_included else [])
    return Generation(
        input_hash=input_hash(task_text, context_text), task_text=(task_text or "").strip(),
        context_text=(context_text or "").strip(), context_included=ctx_included, composed_query=query,
        decomposition_warranted=warranted, subtasks=json.loads(json.dumps(subtasks)), features=features,
        width=w_proto, width_checks={"research_compute_features": w_research, "prototype_dag_width": w_proto,
                                     "agree": True, "meaning": WIDTH_CHECK_MEANING},
        depth=dag_width.depth(subtasks), model=mod.DEFAULT_MODEL, temperature=TEMPERATURE, max_retries=MAX_RETRIES,
        attempts=len(seam.calls), cost_usd=(sum(costs) if costs else None),
        timestamp_utc=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        decompose_sha256=PINNED_SHA256, decompose_commit=PINNED_COMMIT, notes=notes,
    )
