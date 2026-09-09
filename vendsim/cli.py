"""Command-line entry points.

  python3 -m vendsim run  --plan plans/example-plan.json [--days N] [--seed S] [--out runs/name]
  python3 -m vendsim play [--scenario data/scenario-default.json] [--seed S]
  python3 -m vendsim catalogue | locations | machines
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from .model import ROOT, Scenario, load_catalogue, load_locations, load_machines
from .report import format_summary, summarize, write_run
from .sim import Simulation


def _scenario_from_args(args) -> Scenario:
    overrides = {}
    if getattr(args, "location", None):
        overrides["location"] = args.location
    if getattr(args, "machine", None):
        overrides["machine"] = args.machine
    if getattr(args, "seed", None) is not None:
        overrides["seed"] = args.seed
    if getattr(args, "days", None) is not None:
        overrides["days"] = args.days
    return Scenario.load(args.scenario, overrides)


def cmd_run(args) -> int:
    with open(args.plan, encoding="utf-8") as fh:
        plan = json.load(fh)
    if not args.scenario and plan.get("scenario"):
        args.scenario = ROOT / plan["scenario"]
    sc = _scenario_from_args(args)
    sim = Simulation(sc)
    sim.run_plan(plan, days=sc.days)
    out = Path(args.out) if args.out else ROOT / "runs" / f"{sc.name}-{datetime.now():%Y%m%d-%H%M%S}"
    summary = write_run(sim, out)
    print(format_summary(summary))
    print(f"\nWrote {out}/ledger.csv, summary.json, summary.txt, visits.json")
    return 0


def cmd_catalogue(_args) -> int:
    print(f"{'id':<18}{'cost':>7}{'price':>7}{'shelf':>7}  {'fridge':<7}name")
    for p in load_catalogue().values():
        print(f"{p.id:<18}{p.unit_cost:>7.2f}{p.default_price:>7.2f}{p.shelf_life_days:>7}  "
              f"{'yes' if p.refrigerate else 'no':<7}{p.name}")
    return 0


def cmd_locations(_args) -> int:
    for loc in load_locations().values():
        print(f"{loc.id}: {loc.name}")
        print(f"    {loc.description}")
        print(f"    footfall/day {loc.base_footfall:.0f}, stop rate {loc.stop_rate}, rent {loc.monthly_rent:.0f}/mo, "
              f"commission {loc.commission_rate:.0%}, exposure {loc.weather_exposure}, vandalism {loc.vandalism_rate}/day")
    return 0


def cmd_machines(_args) -> int:
    for m in load_machines().values():
        print(f"{m.id}: {m.name}; {m.slots} slots x {m.depth} deep; "
              f"{'refrigerated' if m.refrigerated else 'ambient'}; lease {m.monthly_lease:.0f}/mo; "
              f"power {m.electricity_daily:.2f}/day; card {m.card_share:.0%} at {m.card_fee_rate:.1%}")
    return 0


HELP = """commands
  run <n>                            simulate n days
  set <slot> <product> [price] [qty] queue: assign product, fill to qty (default capacity)
  price <slot> <price>               queue: reprice a slot
  refill                             queue: top up every assigned slot
  remove <slot>                      queue: clear a slot (stock written off)
  commit                             make today's visit with the queued changes
  pending | clear                    show or discard queued changes
  slots | status | catalogue | report
  save <path>                        write ledger/summary to a directory
  quit"""


def cmd_play(args) -> int:
    sc = _scenario_from_args(args)
    sim = Simulation(sc)
    pending: dict = {"set": {}, "price": {}, "remove": [], "refill": False}

    def reset_pending():
        pending.clear()
        pending.update({"set": {}, "price": {}, "remove": [], "refill": False})

    def status():
        print(f"Day {sim.day} ({sim.today:%a %Y-%m-%d})  cash {sim.cash:.2f}  "
              f"machine {'DOWN: ' + sim.down if sim.down else 'ok'}  "
              f"location {sc.location.id}  machine {sc.machine.id}")

    def show_slots():
        for r in sim.stock_table():
            if r["product"]:
                print(f"  {r['slot']:>3}  {r['product']:<18} {r['price']:>6.2f}  {r['units']:>2}/{r['capacity']:<2}  last day {r['soonest_expiry']}")
            else:
                print(f"  {r['slot']:>3}  (empty)")

    print(f"vendsim play: {sc.location.name}; {sc.machine.name}. Type 'help' for commands.")
    status()
    while True:
        try:
            line = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue
        parts = line.split()
        cmd, rest = parts[0].lower(), parts[1:]
        try:
            if cmd in ("quit", "exit", "q"):
                break
            elif cmd == "help":
                print(HELP)
            elif cmd == "run":
                n = int(rest[0]) if rest else 1
                for _ in range(n):
                    r = sim.step()
                    flag = f"  DOWN({r.machine_down})" if r.machine_down else ""
                    ev = "  event" if r.event else ""
                    print(f"  {r.date} {r.weekday} {r.temp_c:>5.1f}C {'rain' if r.precip else '    '} "
                          f"foot {r.footfall:>6} stop {r.stoppers:>3} sold {r.units:>3} "
                          f"gross {r.gross_sales:>7.2f} spoil {r.spoilage_units:>2} cash {r.cash_end:>9.2f}{flag}{ev}")
                status()
            elif cmd == "set":
                slot = int(rest[0])
                spec = {"product": rest[1]}
                if len(rest) > 2:
                    spec["price"] = float(rest[2])
                if len(rest) > 3:
                    spec["fill"] = int(rest[3])
                sim.product(spec["product"])  # validate
                sim.slot(slot)
                pending["set"][slot] = spec
                print(f"  queued: slot {slot} <- {spec}")
            elif cmd == "price":
                slot, price = int(rest[0]), float(rest[1])
                sim.slot(slot)
                pending["price"][slot] = price
                print(f"  queued: slot {slot} price {price:.2f}")
            elif cmd == "refill":
                pending["refill"] = True
                print("  queued: refill all")
            elif cmd == "remove":
                slot = int(rest[0])
                sim.slot(slot)
                pending["remove"].append(slot)
                print(f"  queued: remove slot {slot}")
            elif cmd == "pending":
                print(json.dumps(pending, indent=2))
            elif cmd == "clear":
                reset_pending()
                print("  queue cleared")
            elif cmd == "commit":
                receipt = sim.apply_visit(pending)
                reset_pending()
                print(f"  visit: trip {receipt['visit_cost']:.2f}, stock {receipt['purchases']:.2f}, "
                      f"repairs {receipt['repairs']:.2f}, write-offs {receipt['writeoffs']:.2f}; "
                      f"added {receipt['units_added']}")
                for note in receipt["notes"]:
                    print(f"  {note}")
                status()
            elif cmd in ("slots", "stock"):
                show_slots()
            elif cmd == "status":
                status()
            elif cmd == "catalogue":
                cmd_catalogue(None)
            elif cmd == "report":
                print(format_summary(summarize(sim)))
            elif cmd == "save":
                out = Path(rest[0]) if rest else ROOT / "runs" / f"play-{datetime.now():%Y%m%d-%H%M%S}"
                write_run(sim, out)
                print(f"  wrote {out}")
            else:
                print("  unknown command; 'help' lists them")
        except (ValueError, KeyError, IndexError, RuntimeError) as exc:
            print(f"  error: {exc}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="vendsim", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)

    def common(p):
        p.add_argument("--scenario", help="scenario JSON (default data/scenario-default.json)")
        p.add_argument("--location", help="override the scenario's location id")
        p.add_argument("--machine", help="override the scenario's machine id")
        p.add_argument("--seed", type=int, help="override the random seed")
        p.add_argument("--days", type=int, help="override the number of days")

    p_run = sub.add_parser("run", help="run a scripted plan and write a ledger")
    common(p_run)
    p_run.add_argument("--plan", required=True, help="plan JSON with visits")
    p_run.add_argument("--out", help="output directory (default runs/<scenario>-<timestamp>)")
    p_run.set_defaults(func=cmd_run)

    p_play = sub.add_parser("play", help="interactive turn-by-turn play")
    common(p_play)
    p_play.set_defaults(func=cmd_play)

    for name, fn in (("catalogue", cmd_catalogue), ("locations", cmd_locations), ("machines", cmd_machines)):
        p = sub.add_parser(name, help=f"list {name}")
        p.set_defaults(func=fn)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
