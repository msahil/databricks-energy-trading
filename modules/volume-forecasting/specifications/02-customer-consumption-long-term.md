# 02 — Customer Consumption · Long Term

> Parent brief: [`main.md`](./main.md) (Capability 02). Platform and app conventions: [`instructions.md`](./instructions.md).

## Summary

Forecast **structural demand months to years out** for hedge sizing, retail book planning, and PPA load shapes. Drivers are macroeconomics, **electrification** (EV adoption, heat-pump roll-out), efficiency trends, and population / industrial growth — not next week's weather. Output is **scenario-based and probabilistic** (P50 with P75 / P90 layers) so the curve desk can hedge to the same P-levels it uses on its layered hedge matrix.

This capability reads the historical curated profile (04) as a baseline, applies forward scenario drivers, and publishes **annual / seasonal load shapes** that feed the long-term curve desk and net-volume reconciliation (07). Data is **synthetic**; assumptions are tracked in MLflow so any forecast vintage is reproducible.

## Databricks fit

| Capability | Role |
|---|---|
| **Spark distributed compute** | Scenario simulation across years × driver paths |
| **MLflow** | Track assumptions (EV penetration, heat-pump uptake, GDP) per vintage |
| **Delta time-travel** | Audit exactly which vintage and assumptions drove a hedge |
| **Unity Catalog** | Governed scenario tables; semantics in [`../notebooks/uc_table_comments.py`](../notebooks/uc_table_comments.py) |

## Notebook and tables

[`../notebooks/02_consumption_long_term.ipynb`](../notebooks/02_consumption_long_term.ipynb) materialises:

| Layer | Tables |
|---|---|
| Bronze | `volume_forecast_bronze_macro_drivers` |
| Silver | `volume_forecast_silver_consumption_lt` |
| Gold | `volume_forecast_gold_consumption_lt_shape` |

Reads shared dims + historical `volume_forecast_silver_meter_profile` from **04**.

**Catalog.schema:** `energy_utilities.energy_trading2`. **Grain (illustrative):** monthly / seasonal blocks for `Cal+1` … `Cal+3` per zone; scenarios `BASE`, `HIGH_ELECTRIFICATION`, `LOW_GROWTH`.

---

## Long-term consumption workflow

| # | Trader intent | Data / UI outcome |
|---|---|---|
| 1 | What **annual / seasonal shape** do we hedge? | `volume_forecast_gold_consumption_lt_shape.p50_mw` by season/year |
| 2 | What **P-levels** for layered hedging? | `p50_mw` / `p75_mw` / `p90_mw` per block |
| 3 | How does **electrification** bend the curve? | Scenario comparison (`BASE` vs `HIGH_ELECTRIFICATION`) |
| 4 | What **drivers** underpin the vintage? | `volume_forecast_bronze_macro_drivers` (EV %, heat-pump %, GDP) |
| 5 | How does this vintage differ from the **last**? | `vintage_id` comparison via Delta time-travel |

---

## Datasets

### Bronze — `volume_forecast_bronze_macro_drivers`

Forward structural drivers — grain `vintage_id` × `forecast_year` × `zone_code`.

| Column | Type | Description |
|---|---|---|
| `ingestion_ts` | TIMESTAMP | Landing time |
| `vintage_id` | STRING | Forecast vintage (MLflow run surrogate) |
| `forecast_year` | INT | Target calendar year |
| `zone_code` | STRING | FK → zones |
| `scenario` | STRING | `BASE`, `HIGH_ELECTRIFICATION`, `LOW_GROWTH` |
| `gdp_growth_pct` | DOUBLE | Assumed GDP growth |
| `ev_penetration_pct` | DOUBLE | Share of vehicles electrified |
| `heatpump_penetration_pct` | DOUBLE | Share of heating electrified |
| `efficiency_trend_pct` | DOUBLE | Annual efficiency improvement |

### Silver — `volume_forecast_silver_consumption_lt`

Probabilistic structural demand — grain `vintage_id` × `scenario` × `zone_code` × `forecast_month`.

| Column | Type | Description |
|---|---|---|
| `vintage_id` | STRING | Forecast vintage |
| `scenario` | STRING | Scenario label |
| `zone_code` | STRING | FK → zones |
| `forecast_year` | INT | Target year |
| `forecast_month` | INT | 1–12 |
| `season` | STRING | `WINTER`/`SPRING`/`SUMMER`/`AUTUMN` |
| `p50_mw` | DOUBLE | Median monthly average demand |
| `p75_mw` | DOUBLE | 75th percentile |
| `p90_mw` | DOUBLE | 90th percentile |
| `electrification_uplift_mw` | DOUBLE | Demand added by EV + heat-pump vs base |

### Gold — `volume_forecast_gold_consumption_lt_shape`

Hedge-ready load shape — grain `vintage_id` × `scenario` × `zone_code` × `forecast_year` × `season`.

| Column | Type | Description |
|---|---|---|
| `vintage_id` | STRING | Forecast vintage |
| `scenario` | STRING | Scenario label |
| `zone_code` | STRING | FK → zones |
| `forecast_year` | INT | Target year (`Cal+1` … `Cal+3`) |
| `season` | STRING | Season block |
| `baseload_mw` | DOUBLE | Average baseload volume |
| `peakload_mw` | DOUBLE | Average peak-window volume |
| `p50_mw` | DOUBLE | Median volume for hedge layering |
| `p75_mw` | DOUBLE | 75th percentile (Cal+2 layer) |
| `p90_mw` | DOUBLE | 90th percentile (Cal+3 layer) |
| `as_of_ts` | TIMESTAMP | Vintage publish time |

---

## App UI (Dash) — long-term consumption desk

| Item | Value |
|---|---|
| **Route** | `/volume-forecasting/consumption-long-term` |
| **Sidebar label** | Customer Consumption — Long Term |
| **Page module (convention)** | `app/pages/volume_forecast_consumption_long_term.py` |
| **Data access** | `app/uc_pages.py` + `app/uc_sql.py`; header `sql-warehouse-dropdown` |

### Page layout

| Block | Content |
|---|---|
| **Hero** | Eyebrow, title, trader-facing summary, **Presenter guide** button |
| **Toolbar** | Vintage, scenario, zone, year filter |
| **Status banner** | Cal+1 P50, electrification uplift, scenario selected |
| **Outcome cards** | Baseload, peakload, P90 layer, electrification uplift |
| **Seasonal shape chart** | P50 by season × year, P75/P90 bands |
| **Scenario comparison** | Base vs high-electrification |
| **Driver table** | EV %, heat-pump %, GDP per vintage |
| **Presenter guide** | Problem → hedge link → story → who uses |

### Presenter guide (in-app modal)

| Section | Message |
|---|---|
| What problem this solves | Size multi-year hedges to a credible, electrification-aware load shape |
| How this relates to the curve desk | P50/P75/P90 map to the layered hedge matrix (Cal+1…+3) |
| Story to tell | Seasonal shape → P-levels → electrification bends the curve → driver assumptions |
| Who uses this view | Curve / origination traders, risk, retail planning |

### Widget-to-dataset binding

| UI block | Primary datasets | Key fields |
|---|---|---|
| Status banner | `volume_forecast_gold_consumption_lt_shape` | `p50_mw`, `peakload_mw` |
| Seasonal shape | `volume_forecast_gold_consumption_lt_shape` | `season`, `forecast_year`, `p50_mw`, `p75_mw`, `p90_mw` |
| Scenario comparison | `volume_forecast_silver_consumption_lt` | `scenario`, `p50_mw`, `electrification_uplift_mw` |
| Driver table | `volume_forecast_bronze_macro_drivers` | `ev_penetration_pct`, `heatpump_penetration_pct`, `gdp_growth_pct` |

### Empty and error states

| Condition | Message / behaviour |
|---|---|
| No warehouse selected | Prompt to select a running warehouse |
| Warehouse selected, no data | Prompt to run `energy_trading_demo_data` |
| Query failure | Show error text; do not fabricate charts |

---

## Relationships

| Direction | Dependency |
|---|---|
| **Upstream** | **04** historical profile baseline; macro drivers bronze; shared dims |
| **Downstream** | Long-term curve desk load shapes; **07** structural net-volume context |
| **Shared** | Consumes dims owned by 04 |

## Out of scope

- Real macroeconomic data feeds (synthetic driver assumptions)
- Price / curve modelling (that is the long-term trading desk's job — this module is volume-only)
- Counterparty / PPA contract modelling
- In-app mock or generated series (see [`instructions.md`](./instructions.md))
