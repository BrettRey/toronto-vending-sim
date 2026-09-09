/* vendsim engine: JavaScript port of vendsim/sim.py and report.py.
   Same mechanics and the same data files (injected at build time). The random
   number generator differs from Python's, so a seed here does not reproduce a
   Python run; within this page, the same seed always gives the same game.
   Every number in the data is a placeholder; see notes/source-verification.md. */
(function (global) {
  "use strict";

  const SEGMENTS = ["commuter", "student", "tourist", "resident", "nightlife"];
  const DAYS_PER_MONTH = 365 / 12;
  const DAY_MS = 86400000;

  // ---------------------------------------------------------------- random
  function makeRng(seed) {
    let a = (seed >>> 0) || 1;
    const rng = {
      getState() { return a; },
      setState(s) { a = s >>> 0; },
      random() {
        a |= 0; a = (a + 0x6D2B79F5) | 0;
        let t = Math.imul(a ^ (a >>> 15), 1 | a);
        t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
        return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
      },
      gauss(mu, sigma) {
        let u = 0, v = 0;
        while (u === 0) u = rng.random();
        while (v === 0) v = rng.random();
        return mu + sigma * Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
      },
      poisson(lam) {
        if (lam <= 0) return 0;
        if (lam > 400) return Math.max(0, Math.round(rng.gauss(lam, Math.sqrt(lam))));
        const limit = Math.exp(-lam);
        let k = 0, p = 1;
        for (;;) { p *= rng.random(); if (p <= limit) return k; k += 1; }
      },
    };
    return rng;
  }

  const clamp = (x, lo, hi) => Math.max(lo, Math.min(hi, x));
  const round2 = (x) => Math.round(x * 100) / 100;

  // ---------------------------------------------------------------- dates
  function parseDate(iso) { const [y, m, d] = iso.split("-").map(Number); return Date.UTC(y, m - 1, d); }
  function addDays(ms, n) { return ms + n * DAY_MS; }
  function isoDate(ms) { return new Date(ms).toISOString().slice(0, 10); }
  function weekday(ms) { return (new Date(ms).getUTCDay() + 6) % 7; } // Monday = 0
  function monthIndex(ms) { return new Date(ms).getUTCMonth(); }
  const DOW = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

  // ---------------------------------------------------------------- data
  function normProduct(d) {
    const appeal = {}; SEGMENTS.forEach((s) => { appeal[s] = Number((d.appeal || {})[s] ?? 1); });
    const w = d.weather || {};
    return {
      id: d.id, name: d.name, category: d.category,
      unitCost: Number(d.unit_cost), defaultPrice: Number(d.default_price),
      shelfLifeDays: Number(d.shelf_life_days), refrigerate: Boolean(d.refrigerate),
      maxPerSlot: d.max_per_slot ? Number(d.max_per_slot) : null,
      appeal, weather: { heat: Number(w.heat || 0), cold: Number(w.cold || 0), rain: Number(w.rain || 0) },
    };
  }
  function normLocation(d) {
    const mix = {}; let total = 0;
    SEGMENTS.forEach((s) => { mix[s] = Number((d.segment_mix || {})[s] || 0); total += mix[s]; });
    SEGMENTS.forEach((s) => { mix[s] = mix[s] / total; });
    return {
      id: d.id, name: d.name, description: d.description || "",
      baseFootfall: Number(d.base_footfall), weekdayProfile: d.weekday_profile.map(Number),
      monthProfile: d.month_profile.map(Number), segmentMix: mix, stopRate: Number(d.stop_rate),
      indoor: Boolean(d.indoor), weatherExposure: Number(d.weather_exposure ?? 1),
      monthlyRent: Number(d.monthly_rent || 0), commissionRate: Number(d.commission_rate || 0),
      vandalismRate: Number(d.vandalism_rate || 0),
    };
  }
  function normMachine(d) {
    return {
      id: d.id, name: d.name, slots: Number(d.slots), depth: Number(d.depth),
      refrigerated: Boolean(d.refrigerated), monthlyLease: Number(d.monthly_lease),
      electricityDaily: Number(d.electricity_daily), cardShare: Number(d.card_share),
      cardFeeRate: Number(d.card_fee_rate), jamRate: Number(d.jam_rate),
    };
  }

  function buildScenario(DATA, overrides) {
    const raw = Object.assign({}, DATA["scenario-default"], overrides || {});
    const catalogue = {}; DATA.catalogue.products.forEach((p) => { catalogue[p.id] = normProduct(p); });
    const locations = {}; DATA.locations.locations.forEach((l) => { locations[l.id] = normLocation(l); });
    const machines = {}; DATA.machines.machines.forEach((m) => { machines[m.id] = normMachine(m); });
    if (!locations[raw.location]) throw new Error("unknown location " + raw.location);
    if (!machines[raw.machine]) throw new Error("unknown machine " + raw.machine);
    return {
      name: raw.name, startDate: raw.start_date, days: Number(raw.days), seed: Number(raw.seed),
      location: locations[raw.location], machine: machines[raw.machine],
      startingCash: Number(raw.starting_cash), salesTaxRate: Number(raw.sales_tax_rate),
      visitCost: Number(raw.visit_cost), jamRepairCost: Number(raw.jam_repair_cost),
      vandalismRepairCost: Number(raw.vandalism_repair_cost), localEventRate: Number(raw.local_event_rate),
      localEventMultiplier: Number(raw.local_event_multiplier), priceSensitivity: Number(raw.price_sensitivity),
      outsideOption: Number(raw.outside_option),
      climate: { means: DATA.climate.month_mean_temp_c.map(Number), sd: Number(DATA.climate.daily_temp_sd_c),
                 precip: DATA.climate.precip_day_prob.map(Number) },
      catalogue, locations, machines, overrides: Object.assign({}, overrides || {}),
    };
  }

  // ---------------------------------------------------------------- slots
  function slotUnits(slot) { return slot.lots.reduce((n, l) => n + l.qty, 0); }
  function soonestExpiry(slot) {
    let best = null; slot.lots.forEach((l) => { if (l.qty > 0 && (best === null || l.expires < best)) best = l.expires; });
    return best;
  }

  // ---------------------------------------------------------------- simulation
  class Simulation {
    constructor(scenario, seed) {
      this.sc = scenario;
      this.rng = makeRng(seed == null ? scenario.seed : seed);
      this.day = 0;
      this.cash = scenario.startingCash;
      this.slots = []; for (let i = 1; i <= scenario.machine.slots; i++) this.slots.push({ index: i, product: null, price: 0, lots: [] });
      this.down = "";
      this.ledger = [];
      this.visits = [];
      this.unitsSold = {}; this.revenueByProduct = {}; this.cogsByProduct = {}; this.spoiledByProduct = {};
      this.stockoutDaysBySlot = {};
      this.lostStoppers = 0;
      this._visitToday = { visitCost: 0, purchases: 0, repairs: 0, writeoffs: 0 };
    }

    get startMs() { return parseDate(this.sc.startDate); }
    get todayMs() { return addDays(this.startMs, this.day); }
    get today() { return isoDate(this.todayMs); }
    dateOfDay(d) { return isoDate(addDays(this.startMs, d)); }

    product(pid) { const p = this.sc.catalogue[pid]; if (!p) throw new Error("unknown product " + pid); return p; }
    slot(index) { const i = Number(index); if (!(i >= 1 && i <= this.slots.length)) throw new Error("slot " + index + " out of range"); return this.slots[i - 1]; }
    capacity(product) { const d = this.sc.machine.depth; return product.maxPerSlot ? Math.min(d, product.maxPerSlot) : d; }
    inStock() { return this.slots.filter((s) => s.product && slotUnits(s) > 0); }

    _clear(slot) {
      const units = slotUnits(slot), cost = slot.lots.reduce((c, l) => c + l.qty * l.unitCost, 0);
      slot.lots = []; slot.product = null; slot.price = 0;
      return { units, cost };
    }
    _fill(slot, product, target, receipt) {
      target = Math.min(target, this.capacity(product));
      const need = target - slotUnits(slot);
      if (need <= 0) return;
      slot.lots.push({ qty: need, expires: this.day + product.shelfLifeDays - 1, unitCost: product.unitCost });
      receipt.purchases += need * product.unitCost;
      receipt.unitsAdded[product.id] = (receipt.unitsAdded[product.id] || 0) + need;
    }

    /* actions: {remove: [slot], set: {slot: {product, price, fill}}, price: {slot: p}, refill: true | [slot]} */
    applyVisit(actions) {
      actions = actions || {};
      const receipt = { day: this.day, date: this.today, visitCost: this.sc.visitCost, repairs: 0, purchases: 0,
                        writeoffs: 0, unitsAdded: {}, unitsWrittenOff: 0, notes: [] };
      if (this.down) {
        const cost = this.down === "jam" ? this.sc.jamRepairCost : this.sc.vandalismRepairCost;
        receipt.repairs += cost; receipt.notes.push("repaired " + this.down + " for " + cost.toFixed(2)); this.down = "";
      }
      (actions.remove || []).forEach((idx) => { const r = this._clear(this.slot(idx)); receipt.writeoffs += r.cost; receipt.unitsWrittenOff += r.units; });
      Object.entries(actions.set || {}).forEach(([idx, spec]) => {
        const slot = this.slot(idx), product = this.product(spec.product);
        if (product.refrigerate && !this.sc.machine.refrigerated) throw new Error(product.name + " needs refrigeration; this machine has none");
        if (slot.product && slot.product !== product.id) { const r = this._clear(slot); receipt.writeoffs += r.cost; receipt.unitsWrittenOff += r.units; }
        slot.product = product.id;
        slot.price = Number(spec.price != null ? spec.price : (slot.price || product.defaultPrice));
        if (!(slot.price > 0)) throw new Error("slot " + idx + ": price must be positive");
        const target = spec.fill != null ? Number(spec.fill) : this.capacity(product);
        this._fill(slot, product, target, receipt);
      });
      Object.entries(actions.price || {}).forEach(([idx, price]) => {
        const slot = this.slot(idx);
        if (!slot.product) throw new Error("slot " + idx + ": nothing assigned to reprice");
        if (!(Number(price) > 0)) throw new Error("slot " + idx + ": price must be positive");
        slot.price = Number(price);
      });
      if (actions.refill) {
        const targets = actions.refill === true ? this.slots : actions.refill.map((i) => this.slot(i));
        targets.forEach((slot) => { if (slot.product) { const p = this.product(slot.product); this._fill(slot, p, this.capacity(p), receipt); } });
      }
      this.cash -= receipt.visitCost + receipt.repairs + receipt.purchases;
      this._visitToday.visitCost += receipt.visitCost; this._visitToday.purchases += receipt.purchases;
      this._visitToday.repairs += receipt.repairs; this._visitToday.writeoffs += receipt.writeoffs;
      this.visits.push(receipt);
      return receipt;
    }

    score(product, price, segment, temp, precip) {
      const h = clamp((temp - 15) / 10, -2.5, 2);
      const w = product.weather, ex = this.sc.location.weatherExposure;
      const weatherMult = Math.exp(ex * (w.heat * Math.max(h, 0) + w.cold * Math.max(-h, 0) + w.rain * (precip ? 1 : 0)));
      const priceMult = Math.exp(-this.sc.priceSensitivity * (price / product.defaultPrice - 1));
      return product.appeal[segment] * weatherMult * priceMult;
    }
    _drawSegment() {
      const r = this.rng.random(); let acc = 0;
      for (const s of SEGMENTS) { acc += this.sc.location.segmentMix[s]; if (r < acc) return s; }
      return SEGMENTS[SEGMENTS.length - 1];
    }
    _choose(segment, temp, precip) {
      const options = new Map();
      for (const slot of this.inStock()) {
        const p = this.product(slot.product);
        const cur = options.get(p.id);
        if (!cur) options.set(p.id, { score: this.score(p, slot.price, segment, temp, precip), slot });
        else if (soonestExpiry(slot) < soonestExpiry(cur.slot)) cur.slot = slot;
      }
      if (options.size === 0) return null;
      let total = this.sc.outsideOption; options.forEach((o) => { total += o.score; });
      const r = this.rng.random() * total; let acc = 0;
      for (const o of options.values()) { acc += o.score; if (r < acc) return o.slot; }
      return null;
    }

    step() {
      const sc = this.sc, loc = sc.location, machine = sc.machine;
      const m = monthIndex(this.todayMs), dow = weekday(this.todayMs);
      const temp = this.rng.gauss(sc.climate.means[m], sc.climate.sd);
      const precip = this.rng.random() < sc.climate.precip[m];

      let mult = 1; const ex = loc.weatherExposure;
      if (precip) mult *= 1 - 0.15 * ex;
      if (temp < 0) mult *= 1 - 0.02 * ex * Math.min(-temp, 15);
      if (temp > 28) mult *= 1 - 0.01 * ex * Math.min(temp - 28, 10);
      mult *= Math.exp(this.rng.gauss(0, 0.12));
      const event = this.rng.random() < sc.localEventRate;
      if (event) mult *= sc.localEventMultiplier;
      const footfall = Math.max(0, Math.round(loc.baseFootfall * loc.weekdayProfile[dow] * loc.monthProfile[m] * mult));

      if (!this.down) {
        if (this.rng.random() < machine.jamRate) this.down = "jam";
        else if (this.rng.random() < loc.vandalismRate) this.down = "vandalism";
      }
      const distinct = new Set(this.inStock().map((s) => s.product)).size;
      const variety = distinct === 0 ? 0 : 0.5 + 0.5 * Math.min(distinct, 10) / 10;
      const stoppers = this.down ? 0 : this.rng.poisson(footfall * loc.stopRate * variety);

      let buyers = 0, units = 0, gross = 0, cogs = 0, cardFees = 0;
      for (let i = 0; i < stoppers; i++) {
        const slot = this._choose(this._drawSegment(), temp, precip);
        if (!slot) { this.lostStoppers += 1; continue; }
        const live = slot.lots.filter((l) => l.qty > 0);
        const lot = live.reduce((a, b) => (b.expires < a.expires ? b : a));
        lot.qty -= 1;
        buyers += 1; units += 1; gross += slot.price; cogs += lot.unitCost;
        if (this.rng.random() < machine.cardShare) cardFees += slot.price * machine.cardFeeRate;
        this.unitsSold[slot.product] = (this.unitsSold[slot.product] || 0) + 1;
        this.revenueByProduct[slot.product] = (this.revenueByProduct[slot.product] || 0) + slot.price;
        this.cogsByProduct[slot.product] = (this.cogsByProduct[slot.product] || 0) + lot.unitCost;
      }
      const net = gross / (1 + sc.salesTaxRate), tax = gross - net;
      const commission = net * loc.commissionRate;
      const rent = loc.monthlyRent / DAYS_PER_MONTH, lease = machine.monthlyLease / DAYS_PER_MONTH;
      const electricity = machine.electricityDaily;

      let spoilUnits = 0, spoilCost = 0, stockouts = 0;
      for (const slot of this.slots) {
        if (!slot.product) continue;
        const gone = slot.lots.filter((l) => l.expires <= this.day && l.qty > 0);
        if (gone.length) {
          const u = gone.reduce((n, l) => n + l.qty, 0);
          spoilUnits += u; spoilCost += gone.reduce((c, l) => c + l.qty * l.unitCost, 0);
          this.spoiledByProduct[slot.product] = (this.spoiledByProduct[slot.product] || 0) + u;
        }
        slot.lots = slot.lots.filter((l) => l.expires > this.day && l.qty > 0);
        if (slotUnits(slot) === 0) { stockouts += 1; this.stockoutDaysBySlot[slot.index] = (this.stockoutDaysBySlot[slot.index] || 0) + 1; }
      }
      const running = net - cardFees - commission - rent - lease - electricity;
      this.cash += running;
      const v = this._visitToday;
      const rec = {
        day: this.day, date: this.today, weekday: DOW[dow], tempC: Math.round(temp * 10) / 10, precip, event,
        machineDown: this.down, footfall, stoppers, buyers, units,
        grossSales: round2(gross), salesTax: round2(tax), netSales: round2(net), cogs: round2(cogs),
        cardFees: round2(cardFees), commission: round2(commission), rent: round2(rent), lease: round2(lease),
        electricity: round2(electricity), visitCost: round2(v.visitCost), purchases: round2(v.purchases),
        repairs: round2(v.repairs), writeoffs: round2(v.writeoffs), spoilageUnits: spoilUnits,
        spoilageCost: round2(spoilCost), stockoutSlots: stockouts,
        cashChange: round2(running - v.visitCost - v.purchases - v.repairs), cashEnd: round2(this.cash),
      };
      this.ledger.push(rec);
      this._visitToday = { visitCost: 0, purchases: 0, repairs: 0, writeoffs: 0 };
      this.day += 1;
      return rec;
    }
    run(n) { const out = []; for (let i = 0; i < n; i++) out.push(this.step()); return out; }

    stockTable() {
      return this.slots.map((s) => {
        if (!s.product) return { slot: s.index, product: "", name: "(empty)", price: 0, units: 0, capacity: this.sc.machine.depth, lastDay: null };
        const p = this.product(s.product), e = soonestExpiry(s);
        return { slot: s.index, product: p.id, name: p.name, price: s.price, units: slotUnits(s), capacity: this.capacity(p),
                 lastDay: e === null ? null : e };
      });
    }
    stockAtCost() { return this.slots.reduce((c, s) => c + s.lots.reduce((cc, l) => cc + l.qty * l.unitCost, 0), 0); }

    summarize() {
      const L = this.ledger, days = L.length;
      const tot = (k) => round2(L.reduce((a, r) => a + r[k], 0));
      const products = [];
      for (const [pid, p] of Object.entries(this.sc.catalogue)) {
        const units = this.unitsSold[pid] || 0, spoiled = this.spoiledByProduct[pid] || 0;
        if (!units && !spoiled) continue;
        const revenue = this.revenueByProduct[pid] || 0, net = revenue / (1 + this.sc.salesTaxRate), cogs = this.cogsByProduct[pid] || 0;
        products.push({ product: pid, name: p.name, units, gross: round2(revenue), net: round2(net), cogs: round2(cogs),
                        contribution: round2(net - cogs), spoiledUnits: spoiled, spoiledCost: round2(spoiled * p.unitCost) });
      }
      products.sort((a, b) => b.contribution - a.contribution);
      const worst = Object.entries(this.stockoutDaysBySlot).map(([s, d]) => ({ slot: Number(s), days: d }))
        .sort((a, b) => b.days - a.days).slice(0, 5);
      return {
        scenario: this.sc.name, location: this.sc.location.id, machine: this.sc.machine.id, days,
        startDate: days ? L[0].date : this.sc.startDate, endDate: days ? L[days - 1].date : "",
        startingCash: round2(this.sc.startingCash), finalCash: round2(this.cash), profit: round2(this.cash - this.sc.startingCash),
        stockOnHandAtCost: round2(this.stockAtCost()), visits: this.visits.length,
        daysDown: L.filter((r) => r.machineDown).length,
        units: tot("units"), grossSales: tot("grossSales"), netSales: tot("netSales"), cogs: tot("cogs"),
        cardFees: tot("cardFees"), commission: tot("commission"), rent: tot("rent"), lease: tot("lease"),
        electricity: tot("electricity"), visitCosts: tot("visitCost"), purchases: tot("purchases"), repairs: tot("repairs"),
        writeoffs: tot("writeoffs"), spoilageUnits: tot("spoilageUnits"), spoilageCost: tot("spoilageCost"),
        stoppers: tot("stoppers"), buyers: tot("buyers"), lostStoppers: this.lostStoppers,
        avgUnitsPerDay: days ? Math.round(tot("units") / days * 10) / 10 : 0,
        products, stockoutTop: worst,
      };
    }

    toJSON() {
      return {
        version: 1, overrides: this.sc.overrides, seed: this.sc.seed, rng: this.rng.getState(), day: this.day, cash: this.cash,
        slots: this.slots, down: this.down, ledger: this.ledger, visits: this.visits,
        unitsSold: this.unitsSold, revenueByProduct: this.revenueByProduct, cogsByProduct: this.cogsByProduct,
        spoiledByProduct: this.spoiledByProduct, stockoutDaysBySlot: this.stockoutDaysBySlot,
        lostStoppers: this.lostStoppers, visitToday: this._visitToday,
      };
    }
    static fromJSON(DATA, j) {
      const sc = buildScenario(DATA, Object.assign({}, j.overrides || {}, { seed: j.seed }));
      const sim = new Simulation(sc, j.seed);
      sim.rng.setState(j.rng); sim.day = j.day; sim.cash = j.cash; sim.slots = j.slots; sim.down = j.down || "";
      sim.ledger = j.ledger || []; sim.visits = j.visits || [];
      sim.unitsSold = j.unitsSold || {}; sim.revenueByProduct = j.revenueByProduct || {}; sim.cogsByProduct = j.cogsByProduct || {};
      sim.spoiledByProduct = j.spoiledByProduct || {}; sim.stockoutDaysBySlot = j.stockoutDaysBySlot || {};
      sim.lostStoppers = j.lostStoppers || 0; sim._visitToday = j.visitToday || { visitCost: 0, purchases: 0, repairs: 0, writeoffs: 0 };
      return sim;
    }
  }

  global.VendSim = { SEGMENTS, Simulation, buildScenario, makeRng, slotUnits, soonestExpiry, isoDate, parseDate, addDays, DOW };
})(typeof globalThis !== "undefined" ? globalThis : this);
