"""Data model and loaders.

Reads the JSON files under data/. Each file carries a `_provenance` field
saying where its numbers came from; at the moment every one of them says
"placeholder". Treat the values as game settings, not facts.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
SEGMENTS = ("commuter", "student", "tourist", "resident", "nightlife")


def _load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


@dataclass(frozen=True)
class Product:
    id: str
    name: str
    category: str
    unit_cost: float
    default_price: float
    shelf_life_days: int
    refrigerate: bool
    max_per_slot: int | None
    appeal: dict[str, float]
    weather: dict[str, float]

    @classmethod
    def from_dict(cls, d: dict) -> "Product":
        return cls(
            id=d["id"],
            name=d["name"],
            category=d["category"],
            unit_cost=float(d["unit_cost"]),
            default_price=float(d["default_price"]),
            shelf_life_days=int(d["shelf_life_days"]),
            refrigerate=bool(d["refrigerate"]),
            max_per_slot=d.get("max_per_slot"),
            appeal={s: float(d.get("appeal", {}).get(s, 1.0)) for s in SEGMENTS},
            weather={k: float(d.get("weather", {}).get(k, 0.0)) for k in ("heat", "cold", "rain")},
        )


@dataclass(frozen=True)
class Location:
    id: str
    name: str
    description: str
    base_footfall: float
    weekday_profile: tuple[float, ...]
    month_profile: tuple[float, ...]
    segment_mix: dict[str, float]
    stop_rate: float
    indoor: bool
    weather_exposure: float
    monthly_rent: float
    commission_rate: float
    vandalism_rate: float

    @classmethod
    def from_dict(cls, d: dict) -> "Location":
        wp = tuple(float(x) for x in d["weekday_profile"])
        mp = tuple(float(x) for x in d["month_profile"])
        if len(wp) != 7:
            raise ValueError(f"{d['id']}: weekday_profile needs 7 values")
        if len(mp) != 12:
            raise ValueError(f"{d['id']}: month_profile needs 12 values")
        mix = {s: float(d["segment_mix"].get(s, 0.0)) for s in SEGMENTS}
        total = sum(mix.values())
        if total <= 0:
            raise ValueError(f"{d['id']}: segment_mix sums to zero")
        mix = {s: v / total for s, v in mix.items()}
        return cls(
            id=d["id"],
            name=d["name"],
            description=d.get("description", ""),
            base_footfall=float(d["base_footfall"]),
            weekday_profile=wp,
            month_profile=mp,
            segment_mix=mix,
            stop_rate=float(d["stop_rate"]),
            indoor=bool(d.get("indoor", False)),
            weather_exposure=float(d.get("weather_exposure", 1.0)),
            monthly_rent=float(d.get("monthly_rent", 0.0)),
            commission_rate=float(d.get("commission_rate", 0.0)),
            vandalism_rate=float(d.get("vandalism_rate", 0.0)),
        )


@dataclass(frozen=True)
class MachineType:
    id: str
    name: str
    slots: int
    depth: int
    refrigerated: bool
    monthly_lease: float
    electricity_daily: float
    card_share: float
    card_fee_rate: float
    jam_rate: float

    @classmethod
    def from_dict(cls, d: dict) -> "MachineType":
        return cls(
            id=d["id"],
            name=d["name"],
            slots=int(d["slots"]),
            depth=int(d["depth"]),
            refrigerated=bool(d["refrigerated"]),
            monthly_lease=float(d["monthly_lease"]),
            electricity_daily=float(d["electricity_daily"]),
            card_share=float(d["card_share"]),
            card_fee_rate=float(d["card_fee_rate"]),
            jam_rate=float(d["jam_rate"]),
        )


@dataclass(frozen=True)
class Climate:
    month_mean_temp_c: tuple[float, ...]
    daily_temp_sd_c: float
    precip_day_prob: tuple[float, ...]

    @classmethod
    def from_dict(cls, d: dict) -> "Climate":
        means = tuple(float(x) for x in d["month_mean_temp_c"])
        probs = tuple(float(x) for x in d["precip_day_prob"])
        if len(means) != 12 or len(probs) != 12:
            raise ValueError("climate arrays need 12 monthly values")
        return cls(means, float(d["daily_temp_sd_c"]), probs)


def load_catalogue(path: Path | None = None) -> dict[str, Product]:
    raw = _load_json(path or DATA_DIR / "catalogue.json")
    products = [Product.from_dict(p) for p in raw["products"]]
    ids = [p.id for p in products]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate product ids in catalogue")
    return {p.id: p for p in products}


def load_locations(path: Path | None = None) -> dict[str, Location]:
    raw = _load_json(path or DATA_DIR / "locations.json")
    return {d["id"]: Location.from_dict(d) for d in raw["locations"]}


def load_machines(path: Path | None = None) -> dict[str, MachineType]:
    raw = _load_json(path or DATA_DIR / "machines.json")
    return {d["id"]: MachineType.from_dict(d) for d in raw["machines"]}


def load_climate(path: Path | None = None) -> Climate:
    return Climate.from_dict(_load_json(path or DATA_DIR / "climate.json"))


@dataclass(frozen=True)
class Scenario:
    name: str
    start_date: date
    days: int
    seed: int
    location: Location
    machine: MachineType
    starting_cash: float
    sales_tax_rate: float
    visit_cost: float
    jam_repair_cost: float
    vandalism_repair_cost: float
    local_event_rate: float
    local_event_multiplier: float
    price_sensitivity: float
    outside_option: float
    climate: Climate
    catalogue: dict[str, Product]

    @classmethod
    def load(cls, path: Path | str | None = None, overrides: dict | None = None) -> "Scenario":
        path = Path(path) if path else DATA_DIR / "scenario-default.json"
        raw = _load_json(path)
        raw.update({k: v for k, v in (overrides or {}).items() if v is not None})
        locations = load_locations()
        machines = load_machines()
        if raw["location"] not in locations:
            raise KeyError(f"unknown location {raw['location']!r}; known: {sorted(locations)}")
        if raw["machine"] not in machines:
            raise KeyError(f"unknown machine {raw['machine']!r}; known: {sorted(machines)}")
        return cls(
            name=raw.get("name", path.stem),
            start_date=date.fromisoformat(raw["start_date"]),
            days=int(raw["days"]),
            seed=int(raw["seed"]),
            location=locations[raw["location"]],
            machine=machines[raw["machine"]],
            starting_cash=float(raw["starting_cash"]),
            sales_tax_rate=float(raw["sales_tax_rate"]),
            visit_cost=float(raw["visit_cost"]),
            jam_repair_cost=float(raw["jam_repair_cost"]),
            vandalism_repair_cost=float(raw["vandalism_repair_cost"]),
            local_event_rate=float(raw["local_event_rate"]),
            local_event_multiplier=float(raw["local_event_multiplier"]),
            price_sensitivity=float(raw["price_sensitivity"]),
            outside_option=float(raw["outside_option"]),
            climate=load_climate(),
            catalogue=load_catalogue(),
        )
