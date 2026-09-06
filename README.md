# knowledge-tree

A review tool for your own maths and physics, built ontology-first.

There is deliberately no frontend yet. The point of this stage is to find out
whether the graph you author is any good, before you spend a month rendering it.

## Files

| file | what it is | who edits it |
|---|---|---|
| `nodes.yaml` | the ontology: what exists, what depends on what | you, by hand, in git |
| `state.json` | your review history | written by `review.py` |
| `kt.py` | shared loading and scoring logic | rarely |
| `validate.py` | pre-commit checks | rarely |
| `review.py` | the ranked queue, and logging | rarely |
| `graph.py` | Graphviz dump, diagnostic only | rarely |

The split between `nodes.yaml` and `state.json` is the important architectural
decision. The ontology is stable, shareable and belongs in version control. Your
state changes weekly and needs to be writable from whatever device you are on.
Keep them apart and both stay easy to edit.

## Use

```bash
python3 validate.py                       # run before every commit
python3 review.py                         # what to study now
python3 review.py --branch calculus -n 5
python3 review.py --all                   # include nodes blocked by weak prereqs
python3 review.py log ftc 2 --note "fumbled part 1"
python3 review.py shaky ftc               # toggle a manual flag
python3 graph.py > tree.dot && dot -Tsvg tree.dot -o tree.svg
```

Only dependency is PyYAML.

## The confidence scale

Behavioural, not a feeling. Four levels, each testable in the moment.

- **0** don't recognise it
- **1** recognise it, can't produce it cold
- **2** can do standard problems with notes or a hint
- **3** can do it cold, and can say why it works

## Priority

```
half_life = {0: 3, 1: 7, 2: 21, 3: 60}[confidence]   # days
priority  = (days_since_review / half_life) * importance
```

Never-reviewed nodes sort to the top. A `shaky` flag multiplies by 1.5. That is
the entire model, and it should stay that way. Do not turn this into SM-2:
spaced repetition algorithms are tuned for atomic flashcards, not for
"Fundamental theorem of calculus", and the intervals they produce for a topic
this size do not mean anything.

## Blocking

`review.py` hides any node whose hard prerequisites sit at confidence <= 1,
because reviewing integration by parts while the product rule is broken is
wasted effort. This is the one recommendation a flat list cannot make, and it is
the whole reason the graph structure earns its keep. `--all` overrides it.

In the seeded example, `integration-by-parts` is hidden until `product-rule`
comes up off confidence 1. That is the feature working, not a bug.

## `deps` vs `related`

`deps` means **hard prerequisite**: you literally cannot do this node without
that one. `related` is for everything that merely feels connected, and it is
ignored by layout, blocking and priority.

This distinction is the one that decides whether the project survives. The
temptation is to add every association to `deps`. Give in and every node ends up
adjacent to every other, the layering collapses, blocking fires on everything,
and the picture becomes a hairball. `related` exists as somewhere to put the
urge.

`validate.py` warns above four hard deps for this reason.

## Node fields

```yaml
- id: integration-by-parts     # slug, permanent, referenced by deps -- never rename
  title: Integration by parts
  branch: calculus
  kind: technique              # concept | technique | result | model
  importance: 3                # 1-3
  deps: [product-rule, ftc]
  related: [u-substitution]
  claim: >                     # one sentence, your own words
    Turns the integral of u dv into uv minus the integral of v du.
  practice:                    # REQUIRED -- at least one concrete thing to do
    - "Stewart 8e S7.1 #3-20, 41-45"
  refs:
    - "Stewart 8e S7.1"
```

`kind` decides the default review action: explain a concept out loud, work a
technique cold, re-derive a result from blank paper, state a model's
assumptions.

`practice` is enforced by the validator. A node with nothing to do when it
surfaces gets skipped every time, and enough of those train you to ignore the
queue entirely.

`claim` is optional to the validator but is the highest-value field. If you
cannot state the node in one sentence, you do not have it, which is worth
finding out at authoring time.

## Deliberately absent

No difficulty rating, no estimated time, no continuous mastery percentage, no
hierarchy on top of `deps`, no tags. Each looks useful and each is a field you
maintain forever for a benefit you cannot yet name. Add one only after you have
missed it twice in real use.

## Next

1. Fill `nodes.yaml` out to 30-50 nodes for one branch, straight off a textbook
   table of contents.
2. Run `graph.py` and look at the shape. Hairball at 40 nodes means your `deps`
   are associative.
3. Use `review.py` from the terminal for two weeks. If you do not open it, a
   pretty frontend will not change that, and you have found out cheaply.
4. Only then: static frontend, Cytoscape.js with a layered layout, small JSON
   API on the Pi so you can log from your phone.
