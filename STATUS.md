# STATUS
<!-- SUMMARY: Toronto vending machine simulation; v0.1 engine, placeholder data, tests, and CLI built 2026-09-09; next is Brett's first play session and a decision on which parameters to calibrate · status: active · updated: 2026-09-09 -->

**Last updated:** 2026-09-09
**State:** Playable v0.1. One machine, one location, day-by-day engine with weather, footfall, segment-based choice, spoilage, breakdowns, running costs, and a cash ledger. Five location archetypes, two machine types, eighteen products. Seventeen unittest checks pass. Every data value is a marked placeholder.
**Next action:** Brett plays a first 90-day game (`make play`), or edits `plans/example-plan.json` and runs `make demo`, then says which of the open questions below matter.

## Open questions for Brett

1. **Location.** Five archetypes are provided (subway entrance, campus edge, market laneway, condo lobby, office lobby). Model a specific real spot instead?
2. **Horizon.** The default game is 90 days from mid-September. A full year exposes the campus collapse in summer and the winter footfall drop.
3. **Fleet or single machine.** The engine is one machine. A small fleet would need a shared cash account and a routing cost for visits.
4. **Realism budget.** Which placeholder groups are worth sourcing? `notes/source-verification.md` lists them with where to look. Footfall and wholesale costs change the answers most.
5. **Sidewalk placement.** Whether a machine may stand on a public sidewalk in Toronto is a bylaw question the model doesn't answer; locations carry a flat monthly rent as a stand-in.
6. **A model as operator.** Not built. The engine takes decisions as plain dictionaries, so it's possible. See `DECISIONS.md` on Vending-Bench.

## Session log

### 2026-09-09
- Project scaffolded from Brett's brief: simulate a vending machine on a Toronto street; decide what to stock and how to run it; not a real business.
- Engine, data, plan format, interactive play, scripted runs, reports, and tests written. First demo showed every slot empty most days under weekly refills; the default stop rate was eased so the starting game has slack in both directions.
- Public GitHub repo created; PORTFOLIO row added.
