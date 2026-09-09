# Decisions

2026-09-09 — Location `personal/toronto-vending-sim/`. It's personal software that serves no other project, so `personal/` rather than `tools/`; not a paper, so no LaTeX scaffold.

2026-09-09 — Standard-library Python, seeded RNG, `unittest`. Reason: no install step for Brett, reproducible runs, and the `tools/abm-exploration` precedent (raw Python over a framework).

2026-09-09 — Every value in `data/` is a placeholder and each file says so in a `_provenance` field; `notes/source-verification.md` queues what would calibrate each group. Reason: the source-grounding law. The game needed numbers before anyone had read a source, so they're marked rather than withheld.

2026-09-09 — The operator is a person; the engine takes decisions as plain dictionaries. Neighbour flagged under corpus awareness: Vending-Bench (Backlund and Petersson 2025, arXiv:2502.15840), which Brett holds by way of the Opus 4.8 system card in `literature/`, and his AI-evaluation thread (`papers/retarget/agi-evaluation/`, `papers/development/ai-evaluation-kinds/`). Status: **deliberately distinguished**. This is a game Brett plays, not an evaluation of a model. A model-operator mode is **deferred**, not planned.

2026-09-09 — Customers choose among products, not slots. Stocking the same product in several slots adds capacity, not demand. Reason: simplest defensible choice model; a facings effect can be added later as one multiplier.

2026-09-09 — Shelf life counts the stocking day as day one. A 4-day item stocked Monday sells through Thursday and is purged Thursday night. Reason: matches how a label reads; found as an off-by-one in the first test run.

2026-09-09 — Default subway-entrance stop rate eased from 0.006 to 0.004 after the first 90-day demo had most slots empty on about 75 of 90 days under weekly refills. Reason: the starting game should let a weekly visit roughly keep up, so that both under- and over-stocking are live choices. Both values are guesses.

2026-09-09 — Sidewalk placement is not modelled. Whether a machine may stand on a public sidewalk in Toronto is a bylaw question to look up; each location carries a flat monthly rent as a stand-in for a permit or host fee.

2026-09-09 — Public GitHub under `BrettRey/`, MIT. Reason: portfolio default; nothing private in the repo. Run outputs are gitignored because a plan plus a seed reproduces them.
