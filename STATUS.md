# STATUS
<!-- SUMMARY: Toronto vending machine simulation; v0.2 with a browser interface (clickable slot grid, charts, autosave) over a JS port of the Python engine, all data still placeholder; next is Brett's first play session in the browser · status: active · updated: 2026-09-09 -->

**Last updated:** 2026-09-09
**State:** Playable v0.2. Browser page at `web/index.html`, hosted copy at https://claude.ai/code/artifact/50a8460b-1ce1-4ae0-8771-a0c1b8602eae (private to Brett unless shared). The page runs a JavaScript port of the Python engine; both are tested (18 Python checks, 7 JavaScript checks, plus a freshness check that the built page matches the data). One machine, one location, day-by-day mechanics with weather, footfall, segment-based choice, spoilage, breakdowns, running costs, and a cash ledger. Five location archetypes, two machine types, eighteen products. Every data value is a marked placeholder.
**Next action:** Brett plays in the browser (open the hosted link or `web/index.html`), then says which of the open questions below matter.

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
