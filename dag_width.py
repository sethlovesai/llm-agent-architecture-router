"""Pure-Python DAG width (no networkx, no decomposition-module import).

Re-implements the research definition read from decomposition/decompose.py (read-only):
  * graph: one node per subtask (ALL roles count, including Analyst refusal checks and the final
    Responder); an edge dep -> subtask for every entry in `depends_on`  (_build_graph, decompose.py:100-112)
  * parallelism_width = size of the largest antichain: the largest set of subtasks with no dependency
    path between any pair, computed on the transitive closure      (compute_features, decompose.py:247-282)
  * features are only computed when decomposition_warranted is true; an undecomposed task has no
    features and the router treats it as width 1 (decompose.py:360; router.py load_tasks)
"""
from itertools import combinations


class DagError(ValueError):
    pass


def _validate(subtasks):
    ids = [s["id"] for s in subtasks]
    if len(set(ids)) != len(ids):
        raise DagError("duplicate subtask ids")
    known = set(ids)
    for s in subtasks:
        for d in s["depends_on"]:
            if d not in known:
                raise DagError(f"subtask {s['id']} depends on unknown subtask {d}")
    return ids


def reachability(subtasks):
    """reach[a] = set of subtasks reachable from a (transitive closure). Raises DagError on a cycle."""
    ids = _validate(subtasks)
    children = {i: [] for i in ids}
    for s in subtasks:
        for d in s["depends_on"]:
            children[d].append(s["id"])
    reach, state = {}, {}

    def visit(n):
        if state.get(n) == 1:
            raise DagError("dependency cycle")
        if state.get(n) == 2:
            return reach[n]
        state[n] = 1
        r = set()
        for c in children[n]:
            r.add(c)
            r |= visit(c)
        state[n], reach[n] = 2, r
        return r

    for i in ids:
        visit(i)
    return reach


def max_antichain_width(subtasks):
    """Size of the largest antichain (brute force from the largest size down, as in decompose.py)."""
    if not subtasks:
        raise DagError("empty DAG")
    reach = reachability(subtasks)
    ids = [s["id"] for s in subtasks]
    comparable = lambda a, b: b in reach[a] or a in reach[b]
    for size in range(len(ids), 0, -1):
        for combo in combinations(ids, size):
            if all(not comparable(a, b) for a, b in combinations(combo, 2)):
                return size, list(combo)
    return 1, ids[:1]


def router_width(subtasks, decomposition_warranted=True):
    """Width as the router uses it: the antichain width for a decomposed task, 1 for an undecomposed one."""
    if not decomposition_warranted:
        reachability(subtasks)  # still validate the stored graph
        return 1
    return max_antichain_width(subtasks)[0]


def depth(subtasks):
    """Longest dependency chain in subtasks (node count), for display only."""
    reach = reachability(subtasks)
    parents = {s["id"]: s["depends_on"] for s in subtasks}
    memo = {}

    def d(n):
        if n not in memo:
            memo[n] = 1 + max((d(p) for p in parents[n]), default=0)
        return memo[n]

    return max(d(s["id"]) for s in subtasks) if reach is not None else 0
