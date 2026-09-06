#!/usr/bin/env python3
"""Check nodes.yaml for the mistakes that quietly rot a knowledge graph.

Run this before every commit. Exits non-zero on error.
"""

import sys
from collections import Counter

import yaml

import kt


def main() -> int:
    with open(kt.NODES_PATH) as f:
        raw = yaml.safe_load(f) or []

    errors, warnings = [], []

    ids = [n.get("id") for n in raw]
    for dup, count in Counter(ids).items():
        if count > 1:
            errors.append(f"duplicate id: {dup} (appears {count} times)")
    for i, n in enumerate(raw):
        if not n.get("id"):
            errors.append(f"node #{i} has no id")
        if not n.get("title"):
            errors.append(f"{n.get('id', i)}: no title")

    nodes = kt.load_nodes()

    for nid, n in nodes.items():
        kind = n.get("kind")
        if kind not in kt.KINDS:
            errors.append(f"{nid}: kind {kind!r} not in {sorted(kt.KINDS)}")

        imp = n.get("importance")
        if imp not in (1, 2, 3):
            errors.append(f"{nid}: importance must be 1, 2 or 3 (got {imp!r})")

        # A node with nothing to DO will be skipped every time it surfaces.
        if not n.get("practice"):
            errors.append(f"{nid}: no practice entries (unarmed node)")

        for dep in n.get("deps", []):
            if dep not in nodes:
                errors.append(f"{nid}: dep {dep!r} does not exist")
            if dep == nid:
                errors.append(f"{nid}: depends on itself")

        for rel in n.get("related", []):
            if rel not in nodes:
                warnings.append(f"{nid}: related {rel!r} does not exist")

        if not n.get("claim"):
            warnings.append(f"{nid}: no claim written (can you state it in a sentence?)")

        # Heavy fan-in usually means deps are being used associatively.
        if len(n.get("deps", [])) > 4:
            warnings.append(
                f"{nid}: {len(n['deps'])} hard deps -- are all of these really "
                f"blocking, or do some belong in `related`?"
            )

    for cycle in kt.find_cycles(nodes):
        errors.append("dependency cycle: " + " -> ".join(cycle))

    # Orphans are fine at the roots, suspicious in the middle of a branch.
    for nid, n in nodes.items():
        referenced = any(nid in m.get("deps", []) for m in nodes.values())
        if not n.get("deps") and not referenced:
            warnings.append(f"{nid}: isolated (no deps, nothing depends on it)")

    for w in warnings:
        print(f"warn   {w}")
    for e in errors:
        print(f"ERROR  {e}")

    print(f"\n{len(nodes)} nodes, {len(errors)} errors, {len(warnings)} warnings")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
