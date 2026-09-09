"""The simulation engine: one machine, one location, one day at a time.

A visit (restock, reprice, repair) happens at the start of a day, before
that day's customers. Cash moves at the visit for stock purchases, repairs,
and the trip itself; it moves at the end of the day for sales and running
costs. The ledger row for a day records both.

Mechanics, in order, for each day:
  1. weather (temperature, precipitation) from monthly climate settings;
  2. footfall = base x weekday x month x weather x noise, x event if one fires;
  3. breakdown roll (jam, vandalism): a down machine sells nothing until visited;
  4. stoppers ~ Poisson(footfall x stop_rate x variety), where variety rises
     with the number of distinct products in stock and is 0 for an empty machine;
  5. each stopper draws a segment, then chooses among in-stock products or
     walks away, with probability proportional to
        appeal[segment] x weather multiplier x price multiplier,
     against a fixed outside option;
  6. sales tax is split out of gross, card fees and host commission come off,
     daily rent, lease, and electricity are charged;
  7. expired lots are removed at cost (spoilage) and stockout-days counted.

All functional forms are modelling choices, not estimates. See
notes/model-spec.md.
"""

from __future__ import annotations

import math
import random
from collections import Counter
from dataclasses import dataclass, field, asdict
from datetime import date, timedelta

from .model import SEGMENTS, Product, Scenario

DAYS_PER_MONTH = 365 / 12


def poisson(rng: random.Random, lam: float) -> int:
    """Knuth's method for modest means, normal approximation beyond."""
    if lam <= 0:
        return 0
    if lam > 400:
        return max(0, int(round(rng.gauss(lam, math.sqrt(lam)))))
    limit = math.exp(-lam)
    k = 0
    p = 1.0
    while True:
        p *= rng.random()
        if p <= limit:
            return k
        k += 1


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


@dataclass
class Lot:
    qty: int
    expires: date  # last day the units can be sold; purged that night
    unit_cost: float


@dataclass
class Slot:
    index: int
    product: str | None = None
    price: float = 0.0
    lots: list[Lot] = field(default_factory=list)

    def units(self) -> int:
        return sum(lot.qty for lot in self.lots)

    def soonest_expiry(self) -> date | None:
        live = [lot.expires for lot in self.lots if lot.qty > 0]
        return min(live) if live else None

    def take_one(self) -> Lot:
        """Sell one unit from the lot that expires soonest (FIFO by expiry)."""
        live = [lot for lot in self.lots if lot.qty > 0]
        if not live:
            raise RuntimeError(f"slot {self.index} is empty")
        lot = min(live, key=lambda l: l.expires)
        lot.qty -= 1
        return lot

    def clear(self) -> tuple[int, float]:
        """Remove all stock; returns (units, cost written off)."""
        units = self.units()
        cost = sum(lot.qty * lot.unit_cost for lot in self.lots)
        self.lots = []
        self.product = None
        self.price = 0.0
        return units, cost

    def purge_expired(self, today: date) -> tuple[int, float]:
        gone = [lot for lot in self.lots if lot.expires <= today and lot.qty > 0]
        units = sum(lot.qty for lot in gone)
        cost = sum(lot.qty * lot.unit_cost for lot in gone)
        self.lots = [lot for lot in self.lots if lot.expires > today and lot.qty > 0]
        return units, cost


@dataclass
class DayRecord:
    day: int
    date: str
    weekday: str
    temp_c: float
    precip: bool
    event: bool
    machine_down: str
    footfall: int
    stoppers: int
    buyers: int
    units: int
    gross_sales: float
    sales_tax: float
    net_sales: float
    cogs: float
    card_fees: float
    commission: float
    rent: float
    lease: float
    electricity: float
    visit_cost: float
    purchases: float
    repairs: float
    writeoffs: float
    spoilage_units: int
    spoilage_cost: float
    stockout_slots: int
    cash_change: float
    cash_end: float

    def as_row(self) -> dict:
        return asdict(self)


class Simulation:
    def __init__(self, scenario: Scenario, seed: int | None = None):
        self.sc = scenario
        self.rng = random.Random(scenario.seed if seed is None else seed)
        self.day = 0
        self.cash = scenario.starting_cash
        self.slots = [Slot(i) for i in range(1, scenario.machine.slots + 1)]
        self.down: str = ""
        self.ledger: list[DayRecord] = []
        self.visits: list[dict] = []
        self.units_sold: Counter = Counter()
        self.revenue_by_product: Counter = Counter()
        self.cogs_by_product: Counter = Counter()
        self.spoiled_by_product: Counter = Counter()
        self.stockout_days_by_slot: Counter = Counter()
        self.lost_stoppers = 0
        self._visit_today = {"visit_cost": 0.0, "purchases": 0.0, "repairs": 0.0, "writeoffs": 0.0}

    # ------------------------------------------------------------------ basics
    @property
    def today(self) -> date:
        return self.sc.start_date + timedelta(days=self.day)

    def product(self, pid: str) -> Product:
        try:
            return self.sc.catalogue[pid]
        except KeyError:
            raise KeyError(f"unknown product {pid!r}") from None

    def slot(self, index: int) -> Slot:
        if not 1 <= index <= len(self.slots):
            raise IndexError(f"slot {index} out of range 1..{len(self.slots)}")
        return self.slots[index - 1]

    def capacity(self, product: Product) -> int:
        depth = self.sc.machine.depth
        return min(depth, product.max_per_slot) if product.max_per_slot else depth

    def in_stock(self) -> list[Slot]:
        return [s for s in self.slots if s.product and s.units() > 0]

    # ------------------------------------------------------------------ visits
    def apply_visit(self, actions: dict) -> dict:
        """Apply one visit's actions at the start of today.

        actions keys (all optional):
          "remove": [slot, ...]                       clear slots, stock written off
          "set":    {slot: {"product": id, "price": p, "fill": n}}
                                                      assign and fill (fill defaults to capacity)
          "price":  {slot: p}                         reprice without restocking
          "refill": true | [slot, ...]                top up to capacity at current price
        Every visit costs the trip fee and clears any breakdown at its repair cost.
        """
        receipt = {
            "day": self.day, "date": self.today.isoformat(),
            "visit_cost": self.sc.visit_cost, "repairs": 0.0, "purchases": 0.0,
            "writeoffs": 0.0, "units_added": {}, "units_written_off": 0, "notes": [],
        }
        if self.down:
            cost = self.sc.jam_repair_cost if self.down == "jam" else self.sc.vandalism_repair_cost
            receipt["repairs"] += cost
            receipt["notes"].append(f"repaired {self.down} for {cost:.2f}")
            self.down = ""

        for idx in actions.get("remove", []) or []:
            slot = self.slot(int(idx))
            units, cost = slot.clear()
            receipt["writeoffs"] += cost
            receipt["units_written_off"] += units

        for idx, spec in (actions.get("set", {}) or {}).items():
            slot = self.slot(int(idx))
            product = self.product(spec["product"])
            if product.refrigerate and not self.sc.machine.refrigerated:
                raise ValueError(f"{product.id} needs refrigeration; {self.sc.machine.id} has none")
            if slot.product and slot.product != product.id:
                units, cost = slot.clear()
                receipt["writeoffs"] += cost
                receipt["units_written_off"] += units
            slot.product = product.id
            slot.price = float(spec.get("price", slot.price or product.default_price))
            if slot.price <= 0:
                raise ValueError(f"slot {idx}: price must be positive")
            target = int(spec.get("fill", self.capacity(product)))
            self._fill(slot, product, target, receipt)

        for idx, price in (actions.get("price", {}) or {}).items():
            slot = self.slot(int(idx))
            if not slot.product:
                raise ValueError(f"slot {idx}: nothing assigned to reprice")
            if float(price) <= 0:
                raise ValueError(f"slot {idx}: price must be positive")
            slot.price = float(price)

        refill = actions.get("refill", False)
        if refill:
            targets = self.slots if refill is True else [self.slot(int(i)) for i in refill]
            for slot in targets:
                if slot.product:
                    product = self.product(slot.product)
                    self._fill(slot, product, self.capacity(product), receipt)

        total = receipt["visit_cost"] + receipt["repairs"] + receipt["purchases"]
        self.cash -= total
        for key in ("visit_cost", "repairs", "purchases", "writeoffs"):
            self._visit_today[key] += receipt[key]
        self.visits.append(receipt)
        return receipt

    def _fill(self, slot: Slot, product: Product, target: int, receipt: dict) -> None:
        cap = self.capacity(product)
        target = min(target, cap)
        need = target - slot.units()
        if need <= 0:
            return
        slot.lots.append(Lot(qty=need, expires=self.today + timedelta(days=product.shelf_life_days - 1),
                             unit_cost=product.unit_cost))
        receipt["purchases"] += need * product.unit_cost
        receipt["units_added"][product.id] = receipt["units_added"].get(product.id, 0) + need

    # ------------------------------------------------------------------ demand
    def _weather(self) -> tuple[float, bool]:
        m = self.today.month - 1
        temp = self.rng.gauss(self.sc.climate.month_mean_temp_c[m], self.sc.climate.daily_temp_sd_c)
        precip = self.rng.random() < self.sc.climate.precip_day_prob[m]
        return temp, precip

    def _footfall(self, temp: float, precip: bool) -> tuple[int, bool]:
        loc = self.sc.location
        d = self.today
        base = loc.base_footfall * loc.weekday_profile[d.weekday()] * loc.month_profile[d.month - 1]
        ex = loc.weather_exposure
        mult = 1.0
        if precip:
            mult *= 1 - 0.15 * ex
        if temp < 0:
            mult *= 1 - 0.02 * ex * min(-temp, 15)
        if temp > 28:
            mult *= 1 - 0.01 * ex * min(temp - 28, 10)
        mult *= math.exp(self.rng.gauss(0.0, 0.12))
        event = self.rng.random() < self.sc.local_event_rate
        if event:
            mult *= self.sc.local_event_multiplier
        return max(0, int(round(base * mult))), event

    def score(self, product: Product, price: float, segment: str, temp: float, precip: bool) -> float:
        """Relative attractiveness of one product to one customer. Modelling choice."""
        h = clamp((temp - 15.0) / 10.0, -2.5, 2.0)
        w = product.weather
        ex = self.sc.location.weather_exposure
        weather_mult = math.exp(ex * (w["heat"] * max(h, 0.0) + w["cold"] * max(-h, 0.0) + w["rain"] * (1.0 if precip else 0.0)))
        price_mult = math.exp(-self.sc.price_sensitivity * (price / product.default_price - 1.0))
        return product.appeal[segment] * weather_mult * price_mult

    def _draw_segment(self) -> str:
        r = self.rng.random()
        acc = 0.0
        for seg in SEGMENTS:
            acc += self.sc.location.segment_mix[seg]
            if r < acc:
                return seg
        return SEGMENTS[-1]

    def _choose(self, segment: str, temp: float, precip: bool) -> Slot | None:
        """Pick a slot to buy from, or None to walk away."""
        options: dict[str, tuple[float, Slot]] = {}
        for slot in self.in_stock():
            product = self.product(slot.product)
            if product.id not in options:
                options[product.id] = (self.score(product, slot.price, segment, temp, precip), slot)
            else:
                # same product in several slots: sell from the one expiring soonest
                _, current = options[product.id]
                if slot.soonest_expiry() < current.soonest_expiry():
                    options[product.id] = (options[product.id][0], slot)
        if not options:
            return None
        total = sum(s for s, _ in options.values()) + self.sc.outside_option
        r = self.rng.random() * total
        acc = 0.0
        for score, slot in options.values():
            acc += score
            if r < acc:
                return slot
        return None

    # ------------------------------------------------------------------ the day
    def step(self) -> DayRecord:
        sc = self.sc
        loc, machine = sc.location, sc.machine
        temp, precip = self._weather()
        footfall, event = self._footfall(temp, precip)

        if not self.down:
            if self.rng.random() < machine.jam_rate:
                self.down = "jam"
            elif self.rng.random() < loc.vandalism_rate:
                self.down = "vandalism"

        distinct = len({s.product for s in self.in_stock()})
        variety = 0.0 if distinct == 0 else 0.5 + 0.5 * min(distinct, 10) / 10
        stoppers = 0 if self.down else poisson(self.rng, footfall * loc.stop_rate * variety)

        buyers = units = 0
        gross = cogs = card_fees = 0.0
        for _ in range(stoppers):
            slot = self._choose(self._draw_segment(), temp, precip)
            if slot is None:
                self.lost_stoppers += 1
                continue
            lot = slot.take_one()
            price = slot.price
            buyers += 1
            units += 1
            gross += price
            cogs += lot.unit_cost
            if self.rng.random() < machine.card_share:
                card_fees += price * machine.card_fee_rate
            self.units_sold[slot.product] += 1
            self.revenue_by_product[slot.product] += price
            self.cogs_by_product[slot.product] += lot.unit_cost

        net = gross / (1.0 + sc.sales_tax_rate)
        tax = gross - net
        commission = net * loc.commission_rate
        rent = loc.monthly_rent / DAYS_PER_MONTH
        lease = machine.monthly_lease / DAYS_PER_MONTH
        electricity = machine.electricity_daily

        spoil_units = 0
        spoil_cost = 0.0
        stockouts = 0
        for slot in self.slots:
            if slot.product:
                u, c = slot.purge_expired(self.today)
                if u:
                    spoil_units += u
                    spoil_cost += c
                    self.spoiled_by_product[slot.product] += u
                if slot.units() == 0:
                    stockouts += 1
                    self.stockout_days_by_slot[slot.index] += 1

        running = net - card_fees - commission - rent - lease - electricity
        self.cash += running
        v = self._visit_today
        cash_change = running - v["visit_cost"] - v["purchases"] - v["repairs"]

        rec = DayRecord(
            day=self.day, date=self.today.isoformat(), weekday=self.today.strftime("%a"),
            temp_c=round(temp, 1), precip=precip, event=event, machine_down=self.down,
            footfall=footfall, stoppers=stoppers, buyers=buyers, units=units,
            gross_sales=round(gross, 2), sales_tax=round(tax, 2), net_sales=round(net, 2),
            cogs=round(cogs, 2), card_fees=round(card_fees, 2), commission=round(commission, 2),
            rent=round(rent, 2), lease=round(lease, 2), electricity=round(electricity, 2),
            visit_cost=round(v["visit_cost"], 2), purchases=round(v["purchases"], 2),
            repairs=round(v["repairs"], 2), writeoffs=round(v["writeoffs"], 2),
            spoilage_units=spoil_units, spoilage_cost=round(spoil_cost, 2),
            stockout_slots=stockouts, cash_change=round(cash_change, 2), cash_end=round(self.cash, 2),
        )
        self.ledger.append(rec)
        self._visit_today = {"visit_cost": 0.0, "purchases": 0.0, "repairs": 0.0, "writeoffs": 0.0}
        self.day += 1
        return rec

    def run(self, days: int) -> list[DayRecord]:
        return [self.step() for _ in range(days)]

    # ------------------------------------------------------------------ plans
    def run_plan(self, plan: dict, days: int | None = None) -> list[DayRecord]:
        """Execute a scripted plan: explicit visits by day, plus an optional refill cadence."""
        days = days if days is not None else self.sc.days
        by_day: dict[int, list[dict]] = {}
        for visit in plan.get("visits", []):
            by_day.setdefault(int(visit["day"]), []).append(visit)
        every = plan.get("refill_every")
        for d in range(days):
            actions = by_day.get(d, [])
            if not actions and every and d > 0 and d % int(every) == 0:
                actions = [{"refill": True}]
            for a in actions:
                self.apply_visit(a)
            self.step()
        return self.ledger

    # ------------------------------------------------------------------ views
    def stock_table(self) -> list[dict]:
        rows = []
        for s in self.slots:
            if s.product:
                p = self.product(s.product)
                exp = s.soonest_expiry()
                rows.append({"slot": s.index, "product": p.id, "name": p.name, "price": s.price,
                             "units": s.units(), "capacity": self.capacity(p),
                             "soonest_expiry": exp.isoformat() if exp else ""})
            else:
                rows.append({"slot": s.index, "product": "", "name": "(empty)", "price": 0.0,
                             "units": 0, "capacity": self.sc.machine.depth, "soonest_expiry": ""})
        return rows
