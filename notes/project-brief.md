# Project brief
<!-- SUMMARY: Brett's brief for the vending simulation, what "running the business" means as decisions, scope limits, and realism flags · status: active · updated: 2026-09-09 -->

## Brett's brief (2026-09-09)

> I want to create a new project. This project will simulate a vending machine on the street in Toronto. And I need to decide what to stock, and basically how to run the business. To be clear, it won't be a real business, just a simulation.

## What "running the business" means here

The decisions the simulation exposes, in rough order of how much they move the result:

- **Where the machine stands.** Five archetypes, each with its own footfall, weekly and seasonal shape, customer mix, weather exposure, damage risk, and rent or commission.
- **Which machine.** Ambient snack machine (cheaper, no cold drinks) or refrigerated combo (more slots, cold drinks, higher lease and power).
- **What goes in each slot, and how many facings.** Eighteen products across cold drinks, snacks, one fresh item that spoils in days, and sundries (umbrella, cable, hand warmers, lip balm, sunscreen) that only sell in the right weather.
- **Prices.** Demand falls as price rises above each product's reference price.
- **When to visit.** Each trip costs money; between trips, stock runs down, fresh items expire, and a jammed or vandalised machine sits dark.

## Out of scope for v0.1

Supplier negotiation, bulk pack sizes and delivery minimums, competitors, word of mouth, theft by product, a second machine, and any model-driven operator. Each is a plausible next mechanic; none is planned.

## Realism flags

None of the numbers is sourced. See `source-verification.md`. Two flags matter beyond the numbers:

1. **Sidewalk placement.** A vending machine on a public sidewalk in Toronto raises a permitting question the model doesn't answer. Most real machines sit on private property under a host agreement. The "sidewalk" locations here are a game premise, not a claim that it's allowed.
2. **Tax.** Sales tax is set to 13% (Ontario HST) and taken out of the gross. Whether that's the right treatment for vending sales, and for which products, is unverified.

## Neighbour in Brett's own work

Vending-Bench (Backlund and Petersson 2025, arXiv:2502.15840) is cited in the Opus 4.8 system card held in `literature/`. It has a model run a simulated vending business and scores the bank balance. Brett's AI-evaluation papers are about what such scores license. This project is a game for a person to play; the connection is recorded in `DECISIONS.md` as deliberately distinguished.
