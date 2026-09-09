# CLAUDE.md
<!-- SUMMARY: Agent guidance for the Toronto vending machine simulation; build-steward role; every data value is a marked placeholder until sourced · status: active · updated: 2026-09-09 -->

Guidance for Claude Code, Codex, and other agents working in this repository.
`AGENTS.md` and `GEMINI.md` are symlinks to this file.

## Project

A turn-based simulation of running one vending machine on a Toronto street. Personal project, not research. Public repo under `BrettRey/`, MIT. Brett plays it to decide what to stock, how to price, where to put the machine, and how often to visit.

## Role

Build steward and game designer. Improve the engine, the data, the play experience, and the reports. Keep `make test` green. Don't turn this into a paper or an evaluation harness unless Brett says so (see `DECISIONS.md` on the Vending-Bench neighbour).

## Rules that bite here

- **Source grounding applies to `data/`.** Every number there is a placeholder and each file's `_provenance` field says so. If you change or add a value, either read it from a named source and record where in `notes/source-verification.md`, or leave it marked as a guess. Never promote a guess to a fact by deleting the marker.
- **Don't assert Toronto bylaws, HST treatment, wholesale prices, or climate normals from memory.** Queue them in `notes/source-verification.md` as things to look up.
- **Standard library only.** No third-party packages. Raw Python, as in `tools/abm-exploration`.
- **Deterministic under a seed.** Engine changes that alter the demo output are fine; note them in `DECISIONS.md` so old run folders aren't compared against new ones.
- **Log decisions when made**, in `DECISIONS.md`: `YYYY-MM-DD — Decision. Reason.`
- Portfolio rules (writing style, source grounding, dispatch) live in `../../.claude/rules/` and load automatically in a session opened inside the portfolio.

## Commands

```bash
make test     # python3 -m unittest discover -s tests -v
make demo     # runs plans/example-plan.json, writes runs/demo/
make play     # interactive session
```

## Layout

See `README.md`. The engine's mechanics and every parameter are described in `notes/model-spec.md`.
