# knowledge-tree

A personal review tool for my own maths and physics knowledge. Nodes are topics,
edges are prerequisites. It tells me what to study next.

**Primary use case:** I open this about twice a week to decide what to review.
It is a tool, not a showpiece. When a change trades usefulness for looks, pick
usefulness.

## Architecture

One Flask process (`server.py`) serves both the frontend and the JSON API. No
build step, no npm, no bundler. Deploy is `git pull && systemctl restart`.

- `nodes.yaml` — the ontology. Hand-edited, in git, changes rarely.
- `state.json` — my review history. Written by the app, changes weekly.
- `kt.py` — shared loading and scoring. Both the CLI and the server import it.
- `review.py` — CLI version of the queue.
- `validate.py` — pre-commit checks. Run after any change to `nodes.yaml`.
- `graph.py` — Graphviz dump, diagnostic only.
- `static/index.html` — frontend. Vanilla JS + Cytoscape, no framework.

Keeping the ontology and the state in separate files is deliberate. Do not merge
them.

## Constraints I have already decided. Do not relitigate these.

- **`deps` means hard prerequisite only.** "You cannot do this node without that
  one." Anything merely associated goes in `related`, which is ignored by
  layout, blocking and priority. If `deps` becomes associative the graph turns
  into a hairball and blocking fires on everything.
- **Do not build a spaced-repetition scheduler.** No SM-2, no FSRS, no
  ease factors. The priority formula is
  `(days_since_review / half_life[confidence]) * importance`, one line, and it
  stays that way. SRS algorithms are tuned for atomic flashcards, not for
  "Fundamental theorem of calculus".
- **Every node must have at least one `practice` entry.** Enforced by
  `validate.py`. A node with no concrete action gets skipped every time.
- **Confidence is a 0–3 behavioural scale**, not a feeling. 0 don't recognise
  it, 1 recognise but can't produce cold, 2 can do with hints, 3 cold and can
  say why.
- **The queue is the home screen, the graph is the second tab.** "What should I
  study" is a list question. The graph is for tracing prerequisites.
- **Layered auto-layout (dagre), never a force layout.** Force layouts
  rearrange on every reload and read as a hairball.
- **No auth, by design.** Access is over Tailscale only. Never suggest
  port-forwarding this. If auth ever becomes necessary, say so before writing it.
- **No new node fields** without me asking. Specifically rejected so far:
  difficulty, estimated time, continuous mastery percentage, tags, a hierarchy
  layered on top of `deps`.

## The one feature that justifies the graph

`kt.weak_deps` hides any node whose hard prerequisites sit at confidence <= 1.
Reviewing integration by parts while the product rule is broken is wasted
effort, and this is the recommendation a flat list cannot make. If you touch
priority or blocking logic, preserve this.

## Current state

- API is tested end to end. All endpoints work.
- **The frontend has never been opened in a browser.** Expect small bugs.
- `nodes.yaml` has 14 seed calculus nodes. It needs 30–50 for one branch before
  the tool is genuinely useful.
- Cytoscape is loaded from unpkg. Should be vendored into `static/vendor/`.

## Working with me

- Run `python3 validate.py` after any change to `nodes.yaml`.
- Push back if I ask for something that contradicts the constraints above.
  Tell me it conflicts and why, then do it if I still want it.
- Prefer small diffs over rewrites. Do not refactor things I did not ask about.
- Do not add dependencies without saying why. Current set: Flask, PyYAML,
  waitress. That is meant to stay short — this runs on a Raspberry Pi 4B.
