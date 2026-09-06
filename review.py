#!/usr/bin/env python3
"""The thing you actually open twice a week.

    python3 review.py                        ranked queue
    python3 review.py --branch calculus      filter
    python3 review.py --all                  include blocked nodes
    python3 review.py log ftc 2              record a review at confidence 2
    python3 review.py log ftc 1 --note "..."
    python3 review.py shaky ftc              flag / unflag as shaky
"""

import argparse
import sys
from datetime import date

import kt


def cmd_queue(args) -> None:
    nodes = kt.load_nodes()
    state = kt.load_state()

    rows = []
    for nid, n in nodes.items():
        if args.branch and n.get("branch") != args.branch:
            continue
        weak = kt.weak_deps(nodes, state, nid)
        if weak and not args.all:
            continue  # reviewing on a broken foundation is wasted effort
        rows.append((kt.priority(nodes, state, nid), nid, weak))

    rows.sort(reverse=True)
    if not rows:
        print("Nothing due. Either you are on top of things or the filter is too tight.")
        return

    for score, nid, weak in rows[: args.n]:
        n = nodes[nid]
        c = kt.confidence(state, nid)
        d = kt.days_since(state, nid)
        age = f"{d}d ago" if d is not None else "never reviewed"
        print(f"\n[{score:5.1f}]  {n['title']}  ({nid})")
        print(f"          {n.get('kind', '?')} | conf {c}/3 | {age} | imp {n.get('importance', 2)}")
        print(f"          do: {kt.DEFAULT_ACTION.get(n.get('kind'), 'review it')}")
        for p in n.get("practice", [])[:2]:
            print(f"             - {p}")
        if weak:
            print(f"          BLOCKED by weak prereqs: {', '.join(weak)}")
        if state.get(nid, {}).get("shaky"):
            print("          flagged shaky")

    hidden = sum(
        1
        for nid in nodes
        if kt.weak_deps(nodes, state, nid) and not args.all
    )
    if hidden and not args.all:
        print(f"\n({hidden} nodes hidden because a prerequisite is at confidence <= 1. "
              f"Use --all to see them.)")


def cmd_log(args) -> None:
    nodes = kt.load_nodes()
    if args.id not in nodes:
        raise SystemExit(f"no such node: {args.id}")
    if not 0 <= args.confidence <= kt.CONFIDENCE_MAX:
        raise SystemExit(f"confidence must be 0..{kt.CONFIDENCE_MAX}")

    state = kt.load_state()
    entry = {"date": (args.date or date.today().isoformat()), "confidence": args.confidence}
    if args.note:
        entry["note"] = args.note
    state.setdefault(args.id, {}).setdefault("log", []).append(entry)
    kt.save_state(state)
    print(f"logged {args.id} at confidence {args.confidence} on {entry['date']}")


def cmd_shaky(args) -> None:
    state = kt.load_state()
    cur = state.setdefault(args.id, {}).get("shaky", False)
    state[args.id]["shaky"] = not cur
    kt.save_state(state)
    print(f"{args.id}: shaky = {not cur}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd")

    q = sub.add_parser("queue", help="ranked review queue (default)")
    q.add_argument("--branch")
    q.add_argument("-n", type=int, default=8)
    q.add_argument("--all", action="store_true")
    q.set_defaults(func=cmd_queue)

    l = sub.add_parser("log", help="record a review")
    l.add_argument("id")
    l.add_argument("confidence", type=int)
    l.add_argument("--note")
    l.add_argument("--date", help="YYYY-MM-DD, defaults to today")
    l.set_defaults(func=cmd_log)

    s = sub.add_parser("shaky", help="toggle the shaky flag")
    s.add_argument("id")
    s.set_defaults(func=cmd_shaky)

    # Default to `queue` so `review.py --branch calculus` works bare.
    argv = sys.argv[1:]
    if not argv or argv[0] not in sub.choices and not argv[0] in ("-h", "--help"):
        argv = ["queue"] + argv

    args = p.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
