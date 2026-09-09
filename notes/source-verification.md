# Source verification queue
<!-- SUMMARY: What would have to be read to replace each placeholder parameter group in data/; nothing has been sourced yet except the Vending-Bench citation · status: open · updated: 2026-09-09 -->

Status key: **placeholder** (written from general impressions, unsourced), **verified** (read from the named source, page or record given).

| Parameter group | Status | Where to look | Notes |
|---|---|---|---|
| Base footfall per location | placeholder | City of Toronto open-data pedestrian volume counts at signalised intersections | Pick a real intersection per archetype and use the daily count as `base_footfall`; the weekday and month profiles would need a source with time-of-year coverage. |
| Stop rate, segment mix | placeholder | No obvious public source; an afternoon of counting at a real machine would do more than any document | These two parameters move the result most and are the least defensible. |
| Wholesale unit costs | placeholder | A cash-and-carry wholesaler's price list, or a vending distributor's | Record the date and the pack size; the model currently ignores pack sizes. |
| Retail prices | placeholder | Observed prices on machines in Toronto | Photograph and date them. Reference prices anchor the price-sensitivity term. |
| Shelf lives | placeholder | Product packaging | Fresh items (butter tart) are the ones that matter. |
| Machine lease, electricity, card fees | placeholder | Vending equipment supplier quotes; a payment processor's published pricing | Electricity could be computed from a machine's rated draw and a Toronto residential or commercial tariff. |
| Jam and vandalism rates | placeholder | Operator interviews or trade sources, if any | Outdoor rates are set higher than indoor on assumption only. |
| Rent, commission | placeholder | Host-agreement norms from a vending trade source | Commission on net sales is a common structure but the rates here are guesses. |
| Climate table | placeholder | Environment and Climate Change Canada climate normals for a Toronto station | The monthly means and precipitation-day probabilities here are recollections, not the published table. |
| Sales tax treatment | placeholder | Canada Revenue Agency guidance on HST for vending machine sales | 13% is Ontario's HST rate; which products are taxable through a vending machine is the open question. |
| Sidewalk placement | placeholder | City of Toronto Municipal Code provisions on vending and the public right-of-way | Not modelled; see `project-brief.md`. |
| Vending-Bench citation | **verified** | `literature/anthropic2026opus48SystemCard.md`, reference list entry: Backlund, A., & Petersson, L. (2025). Vending-Bench: A Benchmark for Long-Term Coherence of Autonomous Agents. arXiv:2502.15840 | The paper itself hasn't been read for this project; only the citation is taken from the system card. |
