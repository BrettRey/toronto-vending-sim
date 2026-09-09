# Model specification
<!-- SUMMARY: Mechanics and parameters of the vendsim engine (v0.1); every functional form is a modelling choice and every number a placeholder · status: active · updated: 2026-09-09 -->

All functional forms below are choices made to get a playable game. None was fitted to data. Numbers live in `data/`, each file marked with `_provenance`.

## State

- **Machine:** N slots, each holding one product at one price, with stock kept as lots (quantity, last sellable day, unit cost). Capacity per slot is the machine depth, or the product's `max_per_slot` if smaller (umbrellas, cables).
- **Cash:** one account. Starting cash from the scenario.
- **Down flag:** empty, `jam`, or `vandalism`. Cleared at the next visit.

## A visit (start of a day)

Actions: `remove` slots (stock written off at cost), `set` a slot's product, price, and fill level (a different product already there is written off), `price` a slot, `refill` all or some slots to capacity. Every visit costs the trip fee. A down machine is repaired at the jam or vandalism cost. Stock added is paid at unit cost that day. Refrigerated products can't go in an ambient machine.

## A day, in order

1. **Weather.** Temperature ~ Normal(month mean, daily sd). Precipitation with the month's probability.
2. **Footfall.** `base x weekday[dow] x month[m] x weather x exp(Normal(0, 0.12))`, where weather is `(1 - 0.15 e)` on wet days, `(1 - 0.02 e min(-T, 15))` below 0 C, `(1 - 0.01 e min(T - 28, 10))` above 28 C, and `e` is the location's weather exposure. With probability `local_event_rate` the day is an event and footfall is multiplied by `local_event_multiplier`.
3. **Breakdown.** If not already down: jam with probability `jam_rate`, else vandalism with probability `vandalism_rate`.
4. **Stoppers.** `Poisson(footfall x stop_rate x variety)`, with `variety = 0.5 + 0.5 min(distinct products in stock, 10)/10`, or 0 for an empty or down machine.
5. **Choice.** Each stopper draws a segment from the location mix. For each product in stock, `score = appeal[segment] x weather_mult x price_mult`, where `weather_mult = exp(e (heat x max(h, 0) + cold x max(-h, 0) + rain x wet))`, `h = clamp((T - 15)/10, -2.5, 2)`, and `price_mult = exp(-price_sensitivity x (price/reference - 1))`. The stopper picks product i with probability `score_i / (sum of scores + outside_option)`, otherwise walks away. A product in several slots sells from the slot expiring soonest.
6. **Money.** `net = gross / (1 + tax)`. Card fees are `card_fee_rate x price` on the card share of purchases. Commission is `commission_rate x net`. Rent and lease are charged at 12/365 of the monthly figure; electricity daily.
7. **Spoilage and stockouts.** Lots whose last sellable day is today are removed at cost. Each assigned slot with zero units counts a stockout-day.

## Ledger

One row per day with weather, footfall, stoppers, buyers, units, gross, tax, net, cost of goods sold, card fees, commission, rent, lease, electricity, visit cost, purchases, repairs, write-offs, spoilage, stockout slots, the day's cash change, and closing cash. `cash_change` includes that morning's visit; closing cash reconciles to starting cash plus the column sum (tested).

## Parameters

| Group | File | Notes |
|---|---|---|
| Products: cost, price, shelf life, refrigeration, `max_per_slot`, appeal by segment, weather coefficients | `data/catalogue.json` | 18 products |
| Locations: base footfall, weekday and month profiles, segment mix, stop rate, exposure, rent, commission, vandalism rate | `data/locations.json` | 5 archetypes |
| Machines: slots, depth, refrigeration, lease, electricity, card share and fee, jam rate | `data/machines.json` | 2 types |
| Climate: monthly mean temperature, daily sd, precipitation-day probability | `data/climate.json` | approximate, from memory |
| Scenario: start date, days, seed, starting cash, tax, visit cost, repair costs, event rate and multiplier, price sensitivity, outside option | `data/scenario-default.json` | |

## Known simplifications

Facings don't raise demand. Variety is computed once per day. No competitor, no word of mouth, no theft, no pack sizes or delivery minimums, no hot drinks, no second machine. Weather affects footfall and product appeal but not breakdowns.
