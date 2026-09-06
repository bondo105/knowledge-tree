"""Shared loading, validation and scoring logic for the knowledge tree."""

from __future__ import annotations

import json
import os
from datetime import date, datetime

import yaml

ROOT = os.path.dirname(os.path.abspath(__file__))
NODES_PATH = os.path.join(ROOT, "nodes.yaml")
STATE_PATH = os.path.join(ROOT, "state.json")

KINDS = {"concept", "technique", "result", "model"}

# Confidence scale -- behavioural, not vibes:
#   0  don't recognise it
#   1  recognise it, can't produce it cold
#   2  can do standard problems with notes or a hint
#   3  can do it cold, and can say why it works
CONFIDENCE_MAX = 3

# Days until a node at this confidence is considered fully decayed.
HALF_LIFE = {0: 3, 1: 7, 2: 21, 3: 60}

# What to actually do when a node surfaces, by kind.
DEFAULT_ACTION = {
    "concept": "explain it out loud, unaided",
    "technique": "work problems cold",
    "result": "re-derive it from blank paper",
    "model": "state its assumptions and where it breaks",
}


def load_nodes(path: str = NODES_PATH) -> dict:
    with open(path) as f:
        raw = yaml.safe_load(f) or []
    nodes = {}
    for n in raw:
        n.setdefault("deps", [])
        n.setdefault("related", [])
        n.setdefault("practice", [])
        n.setdefault("refs", [])
        n.setdefault("importance", 2)
        nodes[n["id"]] = n
    return nodes


def load_state(path: str = STATE_PATH) -> dict:
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        return json.load(f)


def save_state(state: dict, path: str = STATE_PATH) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f, indent=2, sort_keys=True)
    os.replace(tmp, path)


def latest(state: dict, node_id: str):
    """Most recent log entry for a node, or None if never reviewed."""
    log = state.get(node_id, {}).get("log", [])
    if not log:
        return None
    return max(log, key=lambda e: e["date"])


def confidence(state: dict, node_id: str) -> int:
    entry = latest(state, node_id)
    return entry["confidence"] if entry else 0


def days_since(state: dict, node_id: str, today: date | None = None):
    entry = latest(state, node_id)
    if not entry:
        return None
    today = today or date.today()
    then = datetime.strptime(entry["date"], "%Y-%m-%d").date()
    return (today - then).days


def priority(nodes: dict, state: dict, node_id: str, today: date | None = None) -> float:
    """Higher means review sooner. Never-reviewed nodes sort to the top."""
    node = nodes[node_id]
    imp = node.get("importance", 2)
    d = days_since(state, node_id, today)
    if d is None:
        return 99.0 * imp
    c = confidence(state, node_id)
    score = (d / HALF_LIFE[c]) * imp
    if state.get(node_id, {}).get("shaky"):
        score *= 1.5
    return score


def weak_deps(nodes: dict, state: dict, node_id: str) -> list[str]:
    """Prerequisites at confidence <= 1. Reviewing on top of these is wasted."""
    return [
        d
        for d in nodes[node_id].get("deps", [])
        if d in nodes and confidence(state, d) <= 1
    ]


def find_cycles(nodes: dict) -> list[list[str]]:
    """Return dependency cycles, if any. Iterative DFS with a colour map."""
    WHITE, GREY, BLACK = 0, 1, 2
    colour = {n: WHITE for n in nodes}
    cycles = []

    for start in nodes:
        if colour[start] != WHITE:
            continue
        stack = [(start, iter(nodes[start].get("deps", [])))]
        path = [start]
        colour[start] = GREY
        while stack:
            node, it = stack[-1]
            advanced = False
            for dep in it:
                if dep not in nodes:
                    continue
                if colour[dep] == GREY:
                    cycles.append(path[path.index(dep):] + [dep])
                elif colour[dep] == WHITE:
                    colour[dep] = GREY
                    path.append(dep)
                    stack.append((dep, iter(nodes[dep].get("deps", []))))
                    advanced = True
                    break
            if not advanced:
                colour[node] = BLACK
                stack.pop()
                path.pop()
    return cycles


def depth(nodes: dict, node_id: str, _seen=None) -> int:
    """Longest prerequisite chain ending at this node. Used for layering."""
    _seen = _seen or set()
    if node_id in _seen:
        return 0
    _seen = _seen | {node_id}
    deps = [d for d in nodes[node_id].get("deps", []) if d in nodes]
    if not deps:
        return 0
    return 1 + max(depth(nodes, d, _seen) for d in deps)
