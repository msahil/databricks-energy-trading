# 03 — Industry Involvement

> Parent brief: [`main.md`](./main.md) (Capability 03). Platform and app conventions: [`instructions.md`](./instructions.md).

## Summary

Model large **industrial and C&I** consumption as a first-class segment. A handful of sites — smelters, chemical plants, data centres, cold stores — can swing the zonal balance more than thousands of households. Their demand follows **production schedules** and shift patterns, and a material share is **demand-side flexible**: load that can shift, shed, or boost for a price.

This capability forecasts the **industrial baseline** and quantifies **dispatchable flexibility** (up / down MW, duration, price). The baseline rolls into total consumption (feeding 07); the flexibility feeds the short-term **DSR & market access** desk's bid stack. Data is **synthetic** but follows industrial-load conventions.

## Databricks fit

| Capability | Role |
|---|---|
| **Lakeflow Declarative Pipelines** | Ingest site SCADA + production schedules → baseline |
| **MLflow** | Baseline vs counterfactual flexibility models |
| **Unity Catalog (Delta Sharing)** | Governed flexibility views shared with the DSR desk |
| **Delta** | Governed tables; semantics in [`../notebooks/uc_table_comments.py`](../notebooks/uc_table_comments.py) |

## Notebook and tables

[`../notebooks/03_industry_involvement.ipynb`](../notebooks/03_industry_involvement.ipynb) materialises:

| Layer | Tables |
|---|---|
| Dimension | `volume_forecast_dim_industrial_sites` |
| Bronze | `volume_forecast_bronze_site_telemetry`, `volume_forecast_bronze_production_schedule` |
| Silver | `volume_forecast_silver_industrial_load` |
| Gold | `volume_forecast_gold_industrial_flexibility` |

Reads shared dims (zones, intervals) from **04**.

**Catalog.schema:** `energy_utilities.energy_trading2`. **Grain (illustrative):** 8–12 industrial sites across five zones; 96 × 15-minute intervals; flexibility products `SHIFT`, `SHED`, `BOOST`.

---

## Industry workflow

| # | Trader intent | Data / UI outcome |
|---|---|---|
| 1 | Which **sites** are drawing now? | `volume_forecast_silver_industrial_load.actual_mw` by site |
| 2 | What's each site's **baseline**? | `baseline_mw` vs `actual_mw` (deviation) |
| 3 | How much **flexible MW** can I count on? | `volume_forecast_gold_industrial_flexibility.flexible_up_mw` / `flexible_down_mw` |
| 4 | At what **price** does flex activate? | `activation_price_eur_mwh`, `min_duration_min` |
| 5 | How does industry shift the **zone total**? | Baseline aggregated to zone, fed to 07 |
| 6 | Which sites are **production-driven** vs weather? | `driver_type` on the site dimension |

---

## Datasets

### Dimension — `volume_forecast_dim_industrial_sites`

| Column | Type | Description |
|---|---|---|
| `site_id` | STRING | Primary key (e.g. `SMELT_DE_001`, `DATACTR_NL_001`) |
| `site_name` | STRING | Label |
| `industry` | STRING | `ALUMINIUM`, `CHEMICALS`, `DATA_CENTRE`, `COLD_STORE`, `STEEL` |
| `zone_code` | STRING | FK → zones |
| `contracted_mw` | DOUBLE | Contracted peak demand |
| `driver_type` | STRING | `PRODUCTION_SCHEDULE`, `CONTINUOUS`, `WEATHER` |
| `is_flexible` | BOOLEAN | Participates in demand-side flexibility |

### Bronze — `volume_forecast_bronze_site_telemetry`

Site metered demand — grain `telemetry_ts` × `site_id`.

| Column | Type | Description |
|---|---|---|
| `ingestion_ts` | TIMESTAMP | Landing time |
| `telemetry_ts` | TIMESTAMP | Measurement time |
| `site_id` | STRING | FK → sites |
| `actual_mw` | DOUBLE | Metered demand |
| `status` | STRING | `RUNNING`, `REDUCED`, `MAINTENANCE` |

### Bronze — `volume_forecast_bronze_production_schedule`

Planned production driving demand — grain `delivery_date` × `site_id` × `shift`.

| Column | Type | Description |
|---|---|---|
| `ingestion_ts` | TIMESTAMP | Landing time |
| `delivery_date` | DATE | Day |
| `site_id` | STRING | FK → sites |
| `shift` | STRING | `DAY`, `SWING`, `NIGHT` |
| `planned_output_units` | DOUBLE | Production volume |
| `expected_mw` | DOUBLE | Demand implied by the plan |

### Silver — `volume_forecast_silver_industrial_load`

Baseline vs actual — grain `interval_start` × `site_id`.

| Column | Type | Description |
|---|---|---|
| `delivery_date` | DATE | Day |
| `interval_start` | TIMESTAMP | Interval |
| `site_id` | STRING | FK → sites |
| `zone_code` | STRING | Denormalised zone |
| `baseline_mw` | DOUBLE | Expected demand (production-driven) |
| `actual_mw` | DOUBLE | Metered (null for future) |
| `deviation_mw` | DOUBLE | `actual − baseline` |

### Gold — `volume_forecast_gold_industrial_flexibility`

Dispatchable flexibility — grain `interval_start` × `site_id` × `flex_product`.

| Column | Type | Description |
|---|---|---|
| `delivery_date` | DATE | Day |
| `interval_start` | TIMESTAMP | Interval |
| `site_id` | STRING | FK → sites |
| `zone_code` | STRING | FK → zones |
| `flex_product` | STRING | `SHIFT`, `SHED`, `BOOST` |
| `flexible_up_mw` | DOUBLE | MW the site can increase (boost) |
| `flexible_down_mw` | DOUBLE | MW the site can reduce (shed/shift) |
| `activation_price_eur_mwh` | DOUBLE | Price to activate the flexibility |
| `min_duration_min` | INT | Minimum sustain duration |
| `availability_status` | STRING | `AVAILABLE`, `ARMED`, `UNAVAILABLE` |

---

## App UI (Dash) — industrial demand & flexibility

| Item | Value |
|---|---|
| **Route** | `/volume-forecasting/industry` |
| **Sidebar label** | Industry Involvement |
| **Page module (convention)** | `app/pages/volume_forecast_industry.py` |
| **Data access** | `app/uc_pages.py` + `app/uc_sql.py`; header `sql-warehouse-dropdown` |

### Page layout

| Block | Content |
|---|---|
| **Hero** | Eyebrow, title, trader-facing summary, **Presenter guide** button |
| **Toolbar** | Date, zone, industry, site filter |
| **Status banner** | Total industrial baseline, total flexible MW, sites armed |
| **Outcome cards** | Baseline MW, flexible-up, flexible-down, avg activation price |
| **Site load chart** | Baseline vs actual by site |
| **Flexibility stack** | Flexible up/down by site, coloured by product |
| **Site table** | Industry, contracted MW, driver type, availability |
| **Presenter guide** | Problem → DSR link → story → who uses |

### Presenter guide (in-app modal)

| Section | Message |
|---|---|
| What problem this solves | A few big sites move the balance — forecast their baseline and harvest their flexibility |
| How this relates to DSR | Flexible MW feeds the short-term DSR bid stack (market access) |
| Story to tell | Who's drawing → baseline vs actual → how much flex → at what price |
| Who uses this view | Industrial desk, DSR / VPP desk, balancing |

### Widget-to-dataset binding

| UI block | Primary datasets | Key fields |
|---|---|---|
| Status banner | `volume_forecast_gold_industrial_flexibility` | `flexible_up_mw`, `flexible_down_mw`, `availability_status` |
| Site load chart | `volume_forecast_silver_industrial_load` | `site_id`, `baseline_mw`, `actual_mw` |
| Flexibility stack | `volume_forecast_gold_industrial_flexibility` | `site_id`, `flex_product`, `flexible_up_mw`, `flexible_down_mw` |
| Site table | `volume_forecast_dim_industrial_sites` | `industry`, `contracted_mw`, `driver_type` |

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
| **Upstream** | **04** shared dims; synthetic site telemetry + production schedules |
| **Downstream** | **07** consumes industrial baseline as part of consumption; short-term **DSR** desk consumes flexibility |
| **Shared** | Consumes zones / intervals owned by 04 |

## Out of scope

- Real industrial SCADA / MES integration (synthetic)
- TSO prequalification rules per flexibility product (illustrative)
- Settlement of activated flexibility (DSR desk concern)
- In-app mock or generated series (see [`instructions.md`](./instructions.md))
