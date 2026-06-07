# Volume forecasting module

Generation, load, and net-volume forecasts that upstream trading desks depend on — see [`specifications/main.md`](specifications/main.md). Implementation rules live in [`specifications/instructions.md`](specifications/instructions.md).

## Capabilities

Domain narrative in [`specifications/main.md`](specifications/main.md) §3; each capability has a detailed sub-spec (datasets, workflow, app UI, lineage):

| # | Capability | Sub-specification |
|---|---|---|
| 01 | Customer Consumption — Short Term | [`01-customer-consumption-short-term.md`](specifications/01-customer-consumption-short-term.md) |
| 02 | Customer Consumption — Long Term | [`02-customer-consumption-long-term.md`](specifications/02-customer-consumption-long-term.md) |
| 03 | Industry Involvement | [`03-industry-involvement.md`](specifications/03-industry-involvement.md) |
| 04 | Smart Metering | [`04-smart-metering.md`](specifications/04-smart-metering.md) |
| 05 | Wind Forecasting | [`05-wind-forecasting.md`](specifications/05-wind-forecasting.md) |
| 06 | Solar Forecasting | [`06-solar-forecasting.md`](specifications/06-solar-forecasting.md) |
| 07 | Publication & Net-Volume Reconciliation | [`07-publication-net-volume.md`](specifications/07-publication-net-volume.md) |
| 08 | Forecast Accuracy & Value | [`08-forecast-accuracy-value.md`](specifications/08-forecast-accuracy-value.md) |

**Overview (presentation only):** [`app/pages/volume_forecast_overview.py`](../../app/pages/volume_forecast_overview.py) — slide deck at `/volume-forecasting/overview`.

**Dash capability routes:** planned under `/volume-forecasting/*` (not yet implemented).

## Run order (planned)

**Smart Metering (04)** is the data backbone — it owns the shared dimensions and curated meter profiles the consumption capabilities (01, 02, 03) read, so it runs first. **Wind (05)** and **Solar (06)** are supply-side. **Publication (07)** reconciles demand + generation into the official net volume; **Accuracy (08)** scores the published result, so it runs last.

```text
04 ─► (01, 02, 03)
      (05, 06)        ─► 07 (publish/reconcile) ─► 08 (accuracy)
```

Job wiring into `energy_trading_demo_data` is **not yet** added — implement notebooks first, then extend the bundle job.

## Unity Catalog target

All tables will use `energy_utilities.energy_trading2` with prefix `volume_forecast_*` (same schema as the short-term module). Override via `DEMO_UC_CATALOG` / `DEMO_UC_SCHEMA`.

## Cross-desk handoff

| Consumer | What they need |
|---|---|
| **Short-term squaring** | Published net volume (07) — short-term consumption (01), wind (05), solar (06), industrial flexibility (03) |
| **Long-term nominations** | Forward load shapes (02) + renewable profiles (05, 06) for hedge sizing and PPA / cannibalization |
| **Short-term DSR** | Industrial demand-side flexibility (03) |
| **Control tower** | Official as-of net volume (07) + severe-deviation context (08) |
| **Risk / management** | Forecast accuracy and cost-of-error in euros (08) |

Trading desks read the **published** net volume (07), not raw capability outputs.

## Disclaimer

All data will be **synthetic** and illustrative. Not a substitute for exchange, TSO, or vendor forecast feeds.
