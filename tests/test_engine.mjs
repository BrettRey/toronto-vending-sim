// Invariants for the JavaScript engine, mirroring tests/test_sim.py. Run: node tests/test_engine.mjs
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import assert from "node:assert/strict";

const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), "..");
vm.runInThisContext(fs.readFileSync(path.join(ROOT, "web/engine.js"), "utf8"));
const DATA = {};
for (const n of ["catalogue", "locations", "machines", "climate", "scenario-default"]) {
  DATA[n] = JSON.parse(fs.readFileSync(path.join(ROOT, "data", n + ".json"), "utf8"));
}
const plan = JSON.parse(fs.readFileSync(path.join(ROOT, "plans/example-plan.json"), "utf8"));
const { Simulation, buildScenario } = globalThis.VendSim;

function runPlan(sim, days) {
  const byDay = {};
  for (const v of plan.visits) (byDay[v.day] ||= []).push(v);
  for (let d = 0; d < days; d++) {
    let actions = byDay[d] || [];
    if (!actions.length && plan.refill_every && d > 0 && d % plan.refill_every === 0) actions = [{ refill: true }];
    for (const a of actions) sim.applyVisit(a);
    sim.step();
  }
}

const tests = {
  determinism() {
    const a = new Simulation(buildScenario(DATA), 7), b = new Simulation(buildScenario(DATA), 7);
    runPlan(a, 30); runPlan(b, 30);
    assert.deepEqual(a.ledger, b.ledger);
  },
  cashReconciles() {
    const sim = new Simulation(buildScenario(DATA));
    runPlan(sim, 60);
    const total = sim.ledger.reduce((s, r) => s + r.cashChange, 0);
    assert.ok(Math.abs(sim.cash - (sim.sc.startingCash + total)) < 0.01 * sim.ledger.length);
    assert.equal(Math.round(sim.cash * 100) / 100, sim.ledger.at(-1).cashEnd);
  },
  unitsConserved() {
    const sim = new Simulation(buildScenario(DATA));
    runPlan(sim, 45);
    const added = sim.visits.reduce((s, v) => s + Object.values(v.unitsAdded).reduce((a, b) => a + b, 0), 0);
    const written = sim.visits.reduce((s, v) => s + v.unitsWrittenOff, 0);
    const sold = Object.values(sim.unitsSold).reduce((a, b) => a + b, 0);
    const spoiled = Object.values(sim.spoiledByProduct).reduce((a, b) => a + b, 0);
    const onHand = sim.slots.reduce((s, sl) => s + sl.lots.reduce((a, l) => a + l.qty, 0), 0);
    assert.equal(added, sold + spoiled + written + onHand);
    assert.ok(sold > 0);
  },
  emptyMachineSellsNothing() {
    const sim = new Simulation(buildScenario(DATA)); sim.run(10);
    assert.equal(sim.ledger.reduce((s, r) => s + r.units, 0), 0);
  },
  spoilage() {
    const sc = buildScenario(DATA);
    sc.location = Object.assign({}, sc.location, { stopRate: 0, vandalismRate: 0 });
    sc.machine = Object.assign({}, sc.machine, { jamRate: 0 });
    const sim = new Simulation(sc);
    sim.applyVisit({ set: { 1: { product: "butter-tart", price: 4 } } });
    sim.run(3);
    assert.equal(globalThis.VendSim.slotUnits(sim.slots[0]), 8);
    sim.step();
    assert.equal(globalThis.VendSim.slotUnits(sim.slots[0]), 0);
    assert.equal(sim.ledger.reduce((s, r) => s + r.spoilageUnits, 0), 8);
  },
  refrigerationGuard() {
    const sim = new Simulation(buildScenario(DATA, { machine: "snack-30" }));
    assert.throws(() => sim.applyVisit({ set: { 1: { product: "cola-355", price: 2.5 } } }));
  },
  saveAndRestore() {
    const a = new Simulation(buildScenario(DATA), 11);
    runPlan(a, 20);
    const b = Simulation.fromJSON(DATA, JSON.parse(JSON.stringify(a.toJSON())));
    a.run(10); b.run(10);
    assert.deepEqual(a.ledger, b.ledger);
    assert.equal(a.cash, b.cash);
  },
};

let failed = 0;
for (const [name, fn] of Object.entries(tests)) {
  try { fn(); console.log("ok   " + name); } catch (e) { failed++; console.log("FAIL " + name + "\n     " + e.message); }
}
console.log(failed ? `${failed} failed` : `all ${Object.keys(tests).length} engine tests passed`);
process.exit(failed ? 1 : 0);
