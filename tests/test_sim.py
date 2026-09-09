"""Engine invariants. Run with: python3 -m unittest discover -s tests -v"""

from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from vendsim.cli import main
from vendsim.model import ROOT, Scenario, load_catalogue, load_locations, load_machines
from vendsim.report import summarize
from vendsim.sim import Simulation

PLAN_PATH = ROOT / "plans" / "example-plan.json"


def load_plan() -> dict:
    with open(PLAN_PATH, encoding="utf-8") as fh:
        return json.load(fh)


class DataTests(unittest.TestCase):
    def test_catalogue_loads_and_prices_exceed_costs(self):
        cat = load_catalogue()
        self.assertGreater(len(cat), 10)
        for p in cat.values():
            self.assertGreater(p.default_price, p.unit_cost, p.id)
            self.assertGreater(p.shelf_life_days, 0, p.id)

    def test_locations_and_machines_load(self):
        locs = load_locations()
        machines = load_machines()
        self.assertGreaterEqual(len(locs), 3)
        self.assertGreaterEqual(len(machines), 2)
        for loc in locs.values():
            self.assertAlmostEqual(sum(loc.segment_mix.values()), 1.0, places=6)

    def test_plan_products_exist(self):
        cat = load_catalogue()
        for visit in load_plan()["visits"]:
            for spec in visit.get("set", {}).values():
                self.assertIn(spec["product"], cat)


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.sc = Scenario.load()
        self.plan = load_plan()

    def test_determinism(self):
        a = Simulation(self.sc, seed=7)
        b = Simulation(self.sc, seed=7)
        a.run_plan(self.plan, days=30)
        b.run_plan(self.plan, days=30)
        self.assertEqual([r.as_row() for r in a.ledger], [r.as_row() for r in b.ledger])
        self.assertAlmostEqual(a.cash, b.cash)

    def test_cash_reconciles_with_ledger(self):
        sim = Simulation(self.sc)
        sim.run_plan(self.plan, days=60)
        total_change = sum(r.cash_change for r in sim.ledger)
        self.assertAlmostEqual(sim.cash, self.sc.starting_cash + total_change, delta=0.01 * len(sim.ledger))
        self.assertEqual(round(sim.cash, 2), sim.ledger[-1].cash_end)

    def test_units_conserved(self):
        sim = Simulation(self.sc)
        sim.run_plan(self.plan, days=45)
        added = sum(sum(v["units_added"].values()) for v in sim.visits)
        written_off = sum(v["units_written_off"] for v in sim.visits)
        sold = sum(sim.units_sold.values())
        spoiled = sum(sim.spoiled_by_product.values())
        on_hand = sum(s.units() for s in sim.slots)
        self.assertEqual(added, sold + spoiled + written_off + on_hand)
        self.assertTrue(all(s.units() >= 0 for s in sim.slots))
        self.assertGreater(sold, 0)

    def test_empty_machine_sells_nothing(self):
        sim = Simulation(self.sc)
        sim.run(10)
        self.assertEqual(sum(r.units for r in sim.ledger), 0)
        self.assertEqual(sum(r.stoppers for r in sim.ledger), 0)

    def test_down_machine_sells_nothing_until_visit(self):
        sim = Simulation(self.sc)
        sim.apply_visit(self.plan["visits"][0])
        sim.down = "jam"
        rec = sim.step()
        self.assertEqual(rec.units, 0)
        self.assertEqual(rec.machine_down, "jam")
        receipt = sim.apply_visit({"refill": True})
        self.assertEqual(receipt["repairs"], self.sc.jam_repair_cost)
        self.assertEqual(sim.down, "")

    def test_spoilage_removes_expired_stock(self):
        quiet = replace(self.sc, location=replace(self.sc.location, stop_rate=0.0, vandalism_rate=0.0),
                        machine=replace(self.sc.machine, jam_rate=0.0))
        sim = Simulation(quiet)
        sim.apply_visit({"set": {"1": {"product": "butter-tart", "price": 4.0}}})
        shelf = self.sc.catalogue["butter-tart"].shelf_life_days
        sim.run(shelf - 1)
        self.assertEqual(sim.slots[0].units(), 8)
        sim.step()
        self.assertEqual(sim.slots[0].units(), 0)
        self.assertEqual(sum(r.spoilage_units for r in sim.ledger), 8)
        self.assertAlmostEqual(sum(r.spoilage_cost for r in sim.ledger), 8 * 1.50, places=2)

    def test_score_falls_as_price_rises(self):
        sim = Simulation(self.sc)
        cola = self.sc.catalogue["cola-355"]
        scores = [sim.score(cola, price, "commuter", 20.0, False) for price in (1.5, 2.5, 3.5, 5.0)]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_weather_moves_demand_the_right_way(self):
        sim = Simulation(self.sc)
        cola = self.sc.catalogue["cola-355"]
        warmers = self.sc.catalogue["hand-warmers"]
        umbrella = self.sc.catalogue["umbrella-compact"]
        self.assertGreater(sim.score(cola, 2.5, "commuter", 30.0, False), sim.score(cola, 2.5, "commuter", 10.0, False))
        self.assertGreater(sim.score(warmers, 3.0, "commuter", -10.0, False), sim.score(warmers, 3.0, "commuter", 15.0, False))
        self.assertGreater(sim.score(umbrella, 12.0, "commuter", 15.0, True), sim.score(umbrella, 12.0, "commuter", 15.0, False))

    def test_refrigeration_guard(self):
        ambient = Scenario.load(overrides={"machine": "snack-30"})
        sim = Simulation(ambient)
        with self.assertRaises(ValueError):
            sim.apply_visit({"set": {"1": {"product": "cola-355", "price": 2.5}}})
        sim.apply_visit({"set": {"1": {"product": "water-500", "price": 2.0}}})
        self.assertEqual(sim.slots[0].units(), 8)

    def test_max_per_slot_caps_fill(self):
        sim = Simulation(self.sc)
        sim.apply_visit({"set": {"1": {"product": "umbrella-compact", "price": 12.0}}})
        self.assertEqual(sim.slots[0].units(), 4)

    def test_refill_cadence_counts_visits(self):
        sim = Simulation(self.sc)
        sim.run_plan(self.plan, days=30)
        self.assertEqual(len(sim.visits), 1 + (29 // 7))

    def test_summary_is_consistent(self):
        sim = Simulation(self.sc)
        sim.run_plan(self.plan, days=30)
        s = summarize(sim)
        self.assertEqual(s["days"], 30)
        self.assertAlmostEqual(s["final_cash"], round(sim.cash, 2))
        self.assertEqual(sum(p["units"] for p in s["products"]), s["units"])


class CliTests(unittest.TestCase):
    def test_run_writes_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "run"
            code = main(["run", "--plan", str(PLAN_PATH), "--days", "10", "--seed", "3", "--out", str(out)])
            self.assertEqual(code, 0)
            for name in ("ledger.csv", "summary.json", "summary.txt", "visits.json"):
                self.assertTrue((out / name).exists(), name)
            with open(out / "summary.json", encoding="utf-8") as fh:
                self.assertEqual(json.load(fh)["days"], 10)

    def test_listings(self):
        for cmd in ("catalogue", "locations", "machines"):
            self.assertEqual(main([cmd]), 0)


if __name__ == "__main__":
    unittest.main()
