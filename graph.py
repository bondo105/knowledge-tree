#!/usr/bin/env python3
"""Dump the graph to Graphviz DOT so you can look at its shape.

    python3 graph.py > tree.dot
    dot -Tsvg tree.dot -o tree.svg     # needs graphviz installed

The point of this script is diagnostic, not decorative. If the picture is a
hairball at 40 nodes, your `deps` are associative rather than blocking, and no
amount of frontend work will fix that.
"""

import sys

import kt

SHAPE = {
    "concept": "ellipse",
    "technique": "box",
    "result": "diamond",
    "model": "hexagon",
}

# Fill by current confidence: dark = solid, pale = decayed or never seen.
FILL = {0: "#ffffff", 1: "#fde2e2", 2: "#fff3cd", 3: "#d4edda"}


def main() -> None:
    nodes = kt.load_nodes()
    state = kt.load_state()

    out = sys.stdout
    out.write("digraph knowledge {\n")
    out.write('  rankdir=BT;\n')
    out.write('  node [style=filled, fontname="Helvetica", fontsize=10];\n')
    out.write('  edge [color="#666666"];\n')

    branches = {}
    for nid, n in nodes.items():
        branches.setdefault(n.get("branch", "misc"), []).append(nid)

    for branch, members in sorted(branches.items()):
        out.write(f'  subgraph "cluster_{branch}" {{\n')
        out.write(f'    label="{branch}"; color="#cccccc";\n')
        for nid in sorted(members):
            n = nodes[nid]
            c = kt.confidence(state, nid)
            shape = SHAPE.get(n.get("kind"), "box")
            pen = 2.0 if n.get("importance", 2) == 3 else 1.0
            label = n["title"].replace('"', "'")
            out.write(
                f'    "{nid}" [label="{label}", shape={shape}, '
                f'fillcolor="{FILL[c]}", penwidth={pen}];\n'
            )
        out.write("  }\n")

    for nid, n in nodes.items():
        for dep in n.get("deps", []):
            if dep in nodes:
                out.write(f'  "{dep}" -> "{nid}";\n')
        for rel in n.get("related", []):
            if rel in nodes and nid < rel:
                out.write(
                    f'  "{nid}" -> "{rel}" [style=dashed, dir=none, '
                    f'color="#dddddd", constraint=false];\n'
                )

    out.write("}\n")


if __name__ == "__main__":
    main()
