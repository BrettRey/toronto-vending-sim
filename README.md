# Toronto vending machine simulation

A turn-based simulation of running one vending machine on a Toronto street. You choose where it stands, what goes in each slot, what each item costs, and how often you go out to refill it. The simulation decides who walks past, who stops, what they buy, what spoils, and what breaks. It isn't a real business and isn't meant to become one.

## The numbers are placeholders

Every parameter under `data/` was written from general impressions so the game would run. Footfall, stop rates, wholesale costs, retail prices, shelf lives, rents, lease and electricity costs, breakdown rates, and the climate table are all guesses. Each data file says so in its `_provenance` field, and `notes/source-verification.md` lists what would have to be read to calibrate each group. Don't quote a result from this simulation as a fact about vending in Toronto.

## Play it in the browser

Open `web/index.html` in any browser, or use the hosted copy linked from `STATUS.md`. The machine is drawn as a grid of slots. Click a slot to choose a product, price, and fill level; queue as many changes as you like; then make the visit and run a day or a week. Cash, units sold, and a by-product table update as you go, and progress is saved in the browser.

The page is self-contained: `web/engine.js` is a JavaScript port of the Python engine and the data files are embedded at build time by `scripts/build_web.py` (`make web`). A test fails if the page falls behind the data. The two engines share mechanics and data but not a random number generator, so a seed in one doesn't reproduce a run in the other.

## Command line

Python 3.10 or later, standard library only.

```bash
make test        # engine invariants
make demo        # 90 days on the example plan; writes runs/demo/
make play        # interactive, one visit at a time
python3 -m vendsim catalogue
python3 -m vendsim locations
python3 -m vendsim machines
```

## How a day works

1. Weather is drawn from the month's settings (temperature, whether it rains or snows).
2. Footfall is the location's base count, scaled by weekday, month, weather, and noise. Some days a local event doubles it.
3. The machine can jam or be vandalised. A machine that's down sells nothing until you visit.
4. Some passers-by stop. More distinct products in stock means more stop; an empty machine gets none.
5. Each stopper belongs to a segment (commuter, student, tourist, resident, nightlife) and picks among what's in stock or walks away. Appeal to their segment, the weather, and your price relative to a reference price all shift the odds.
6. Sales tax comes out of the gross. Card fees, any host commission, and the daily share of rent, lease, and electricity are charged.
7. Anything past its last sellable day is thrown out at cost. Empty slots are counted as stockout-days.

A visit happens at the start of a day, before that day's customers. It costs a trip fee, repairs any breakdown, and pays for the stock you add. Removing a product writes off what's left of it.

## Playing

`make play` opens a prompt. Queue changes with `set`, `price`, `refill`, and `remove`, then `commit` to make the visit, then `run 7` to watch a week go by. `slots` shows the machine, `report` the running totals, `save` writes a ledger. `help` lists everything.

```
> set 1 cola-355 2.50
> set 2 water-500 2.00
> commit
> run 7
```

## Scripted plans

A plan file lists visits by day, plus an optional refill cadence. `plans/example-plan.json` is a first unoptimised assortment for the 40-slot refrigerated machine with weekly refills. Copy it, change it, and run it:

```bash
python3 -m vendsim run --plan plans/my-plan.json --days 365 --seed 11 --out runs/my-plan
python3 -m vendsim run --plan plans/example-plan.json --location campus-edge --machine snack-30
```

Each run writes `ledger.csv` (one row per day), `summary.json`, `summary.txt`, and `visits.json`. The same plan and seed always give the same result, so two plans can be compared fairly.

## Layout

```
data/           catalogue, locations, machines, climate, default scenario (all placeholder values)
plans/          scripted operator plans
vendsim/        the engine: model.py (loaders), sim.py (the day step), report.py, cli.py
web/            template.html + engine.js -> index.html (built by scripts/build_web.py)
tests/          Python and JavaScript engine invariants, plus a freshness check on the built page
notes/          project brief, model spec, source-verification queue
runs/           run outputs (ignored by git)
```

## Related work

Vending-Bench (Backlund and Petersson 2025, arXiv:2502.15840) has a language model run a simulated vending business for a year and scores its bank balance. This project is the other way round. The operator is a person, and the engine only asks that decisions arrive as a small dictionary, which would let a model be plugged in later if that ever became interesting.

## License

MIT.
