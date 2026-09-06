#!/usr/bin/env python3
"""One process, serving the frontend and the JSON API.

    pip install flask pyyaml waitress
    python3 server.py                 # dev, binds 127.0.0.1:8080
    python3 server.py --host 0.0.0.0  # reachable from the rest of the LAN

There is no authentication here on purpose. Anyone who can reach the port can
rewrite your review history. Do NOT port-forward this to the open internet --
see the README for why Tailscale is the right answer instead.
"""

import argparse
from datetime import date

from flask import Flask, jsonify, request, send_from_directory

import kt

app = Flask(__name__, static_folder="static", static_url_path="/static")


@app.get("/")
def index():
    return send_from_directory("static", "index.html")


@app.get("/api/graph")
def api_graph():
    """The ontology, plus a layer index so the frontend can rank nodes."""
    nodes = kt.load_nodes()
    out = []
    for nid, n in nodes.items():
        out.append(
            {
                "id": nid,
                "title": n["title"],
                "branch": n.get("branch", "misc"),
                "kind": n.get("kind"),
                "importance": n.get("importance", 2),
                "deps": [d for d in n.get("deps", []) if d in nodes],
                "related": [r for r in n.get("related", []) if r in nodes],
                "claim": (n.get("claim") or "").strip(),
                "practice": n.get("practice", []),
                "refs": n.get("refs", []),
                "layer": kt.depth(nodes, nid),
                "action": kt.DEFAULT_ACTION.get(n.get("kind"), "review it"),
            }
        )
    return jsonify(sorted(out, key=lambda n: (n["layer"], n["id"])))


@app.get("/api/state")
def api_state():
    """Per-node derived state: what the frontend needs to colour and sort."""
    nodes = kt.load_nodes()
    state = kt.load_state()
    out = {}
    for nid in nodes:
        out[nid] = {
            "confidence": kt.confidence(state, nid),
            "days_since": kt.days_since(state, nid),
            "priority": round(kt.priority(nodes, state, nid), 1),
            "shaky": state.get(nid, {}).get("shaky", False),
            "weak_deps": kt.weak_deps(nodes, state, nid),
            "log": state.get(nid, {}).get("log", []),
        }
    return jsonify(out)


@app.get("/api/queue")
def api_queue():
    """The ranked list. This, not the graph, is the home screen."""
    nodes = kt.load_nodes()
    state = kt.load_state()
    branch = request.args.get("branch")
    include_blocked = request.args.get("all") == "1"

    rows = []
    for nid, n in nodes.items():
        if branch and n.get("branch") != branch:
            continue
        weak = kt.weak_deps(nodes, state, nid)
        if weak and not include_blocked:
            continue
        rows.append(
            {
                "id": nid,
                "title": n["title"],
                "kind": n.get("kind"),
                "action": kt.DEFAULT_ACTION.get(n.get("kind"), "review it"),
                "practice": n.get("practice", []),
                "priority": round(kt.priority(nodes, state, nid), 1),
                "confidence": kt.confidence(state, nid),
                "days_since": kt.days_since(state, nid),
                "blocked_by": weak,
            }
        )
    rows.sort(key=lambda r: -r["priority"])
    return jsonify(rows)


@app.post("/api/log")
def api_log():
    body = request.get_json(force=True) or {}
    nid = body.get("id")
    conf = body.get("confidence")

    nodes = kt.load_nodes()
    if nid not in nodes:
        return jsonify({"error": f"no such node: {nid}"}), 404
    if not isinstance(conf, int) or not 0 <= conf <= kt.CONFIDENCE_MAX:
        return jsonify({"error": f"confidence must be an int 0..{kt.CONFIDENCE_MAX}"}), 400

    entry = {"date": body.get("date") or date.today().isoformat(), "confidence": conf}
    if body.get("note"):
        entry["note"] = str(body["note"])[:500]

    state = kt.load_state()
    state.setdefault(nid, {}).setdefault("log", []).append(entry)
    kt.save_state(state)
    return jsonify({"ok": True, "id": nid, "entry": entry})


@app.post("/api/shaky")
def api_shaky():
    body = request.get_json(force=True) or {}
    nid = body.get("id")
    if nid not in kt.load_nodes():
        return jsonify({"error": f"no such node: {nid}"}), 404
    state = kt.load_state()
    cur = state.setdefault(nid, {}).get("shaky", False)
    state[nid]["shaky"] = not cur
    kt.save_state(state)
    return jsonify({"ok": True, "id": nid, "shaky": not cur})


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8080)  # 80 is taken by Pi-hole
    p.add_argument("--dev", action="store_true", help="Flask reloader, noisy")
    args = p.parse_args()

    if args.dev:
        app.run(host=args.host, port=args.port, debug=True)
    else:
        try:
            from waitress import serve

            print(f"serving on http://{args.host}:{args.port}")
            serve(app, host=args.host, port=args.port)
        except ImportError:
            print("waitress not installed, falling back to the Flask server")
            app.run(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
