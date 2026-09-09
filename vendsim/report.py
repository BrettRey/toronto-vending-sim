"""Summaries and file output for a finished (or paused) simulation."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from .sim import Simulation


def summarize(sim: Simulation) -> dict:
    L = sim.ledger
    days = len(L)
    tot = lambda key: round(sum(getattr(r, key) for r in L), 2)  # noqa: E731
    products = []
    for pid, product in sim.sc.catalogue.items():
        units = sim.units_sold.get(pid, 0)
        spoiled = sim.spoiled_by_product.get(pid, 0)
        if units == 0 and spoiled == 0:
            continue
        revenue = sim.revenue_by_product.get(pid, 0.0)
        net = revenue / (1 + sim.sc.sales_tax_rate)
        cogs = sim.cogs_by_product.get(pid, 0.0)
        products.append({
            "product": pid, "name": product.name, "units": units,
            "gross": round(revenue, 2), "net": round(net, 2), "cogs": round(cogs, 2),
            "contribution": round(net - cogs, 2), "spoiled_units": spoiled,
            "spoiled_cost": round(spoiled * product.unit_cost, 2),
        })
    products.sort(key=lambda r: r["contribution"], reverse=True)
    worst_slots = sorted(sim.stockout_days_by_slot.items(), key=lambda kv: kv[1], reverse=True)[:5]
    return {
        "scenario": sim.sc.name,
        "location": sim.sc.location.id,
        "machine": sim.sc.machine.id,
        "days": days,
        "start_date": L[0].date if L else sim.sc.start_date.isoformat(),
        "end_date": L[-1].date if L else "",
        "starting_cash": round(sim.sc.starting_cash, 2),
        "final_cash": round(sim.cash, 2),
        "profit": round(sim.cash - sim.sc.starting_cash, 2),
        "stock_on_hand_at_cost": round(sum(l.qty * l.unit_cost for s in sim.slots for l in s.lots), 2),
        "visits": len(sim.visits),
        "days_down": sum(1 for r in L if r.machine_down),
        "units": tot("units"),
        "gross_sales": tot("gross_sales"),
        "net_sales": tot("net_sales"),
        "cogs": tot("cogs"),
        "card_fees": tot("card_fees"),
        "commission": tot("commission"),
        "rent": tot("rent"),
        "lease": tot("lease"),
        "electricity": tot("electricity"),
        "visit_costs": tot("visit_cost"),
        "purchases": tot("purchases"),
        "repairs": tot("repairs"),
        "writeoffs": tot("writeoffs"),
        "spoilage_units": tot("spoilage_units"),
        "spoilage_cost": tot("spoilage_cost"),
        "stoppers": tot("stoppers"),
        "buyers": tot("buyers"),
        "lost_stoppers": sim.lost_stoppers,
        "avg_units_per_day": round(tot("units") / days, 1) if days else 0.0,
        "products": products,
        "stockout_days_by_slot_top5": [{"slot": s, "days": d} for s, d in worst_slots],
    }


def format_summary(summary: dict) -> str:
    s = summary
    lines = [
        f"Scenario {s['scenario']}: {s['location']} / {s['machine']}, {s['days']} days "
        f"({s['start_date']} to {s['end_date']})",
        f"Cash {s['starting_cash']:.2f} -> {s['final_cash']:.2f}  (profit {s['profit']:+.2f}; "
        f"stock on hand at cost {s['stock_on_hand_at_cost']:.2f})",
        f"Units {s['units']}  avg/day {s['avg_units_per_day']}  stoppers {s['stoppers']}  "
        f"buyers {s['buyers']}  walked away {s['lost_stoppers']}  days down {s['days_down']}  visits {s['visits']}",
        f"Gross {s['gross_sales']:.2f}  net {s['net_sales']:.2f}  COGS {s['cogs']:.2f}  "
        f"card fees {s['card_fees']:.2f}  commission {s['commission']:.2f}",
        f"Rent {s['rent']:.2f}  lease {s['lease']:.2f}  electricity {s['electricity']:.2f}  "
        f"visits {s['visit_costs']:.2f}  repairs {s['repairs']:.2f}  purchases {s['purchases']:.2f}",
        f"Spoilage {s['spoilage_units']} units / {s['spoilage_cost']:.2f}  write-offs {s['writeoffs']:.2f}",
        "",
        f"{'product':<18}{'units':>7}{'net':>10}{'cogs':>10}{'contrib':>10}{'spoiled':>9}",
    ]
    for p in s["products"]:
        lines.append(f"{p['product']:<18}{p['units']:>7}{p['net']:>10.2f}{p['cogs']:>10.2f}"
                     f"{p['contribution']:>10.2f}{p['spoiled_units']:>9}")
    if s["stockout_days_by_slot_top5"]:
        worst = ", ".join(f"slot {r['slot']} ({r['days']}d)" for r in s["stockout_days_by_slot_top5"])
        lines.append("")
        lines.append(f"Most stockout-days: {worst}")
    return "\n".join(lines)


def write_run(sim: Simulation, out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = [r.as_row() for r in sim.ledger]
    with open(out_dir / "ledger.csv", "w", newline="", encoding="utf-8") as fh:
        if rows:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
    summary = summarize(sim)
    with open(out_dir / "summary.json", "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)
    with open(out_dir / "visits.json", "w", encoding="utf-8") as fh:
        json.dump(sim.visits, fh, indent=2)
    with open(out_dir / "summary.txt", "w", encoding="utf-8") as fh:
        fh.write(format_summary(summary) + "\n")
    return summary
