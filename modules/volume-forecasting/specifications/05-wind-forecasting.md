# 05 — Wind Forecasting

> Parent brief: [`main.md`](./main.md) (Capability 05). Platform and app conventions: [`instructions.md`](./instructions.md).

## Summary

Forecast **wind generation** at 15-minute grain across the onshore and offshore fleet. Wind is the largest source of **volume uncertainty** in a Northern-European book — a 2 m/s shift in forecast wind speed can swing hundreds of MW. The forecast is **probabilistic** (P10 / P50 / P90 per asset / interval / vintage) and uses an **ensemble** of numerical weather prediction (NWP) sources blended against SCADA history.

This is a **supply leg** of net volume: it owns the wind asset registry, ingests NWP ensembles + turbine telemetry, and publishes asset- and zone-level generation forecasts that feed net-volume reconciliation (07) and the accuracy desk (08). Data is **synthetic** but follows power-curve and ensemble conventions.

## Databricks fit

| Capability | Role |
|---|---|
| **Structured Streaming** | NWP refresh + SCADA telemetry ingest (demo materialises gold in batch) |
| **Feature Store** | Power-curve features (wind speed, direction, density) per asset |
| **MLflow** | Power-curve / ensemble-blend models; champion tracked for accuracy (08) |
| **Delta** | Governed forecast tables; semantics in [`../notebooks/uc_table_comments.py`](../notebooks/uc_table_comments.py) |

## Notebook and tables

[`../notebooks/05_wind_forecasting.ipynb`](../notebooks/05_wind_forecasting.ipynb) materialises:

| Layer | Tables |
|---|---|
| Dimension | `volume_forecast_dim_wind_assets` |
| Bronze | `volume_forecast_bronze_nwp_wind`, `volume_forecast_bronze_wind_scada` |
| Silver | `volume_forecast_silver_wind_forecast` |
| Gold | `volume_forecast_gold_wind_summary` |

Reads shared dims (zones, intervals) from **04**. Owns the wind asset registry.

**Catalog.schema:** `energy_utilities.energy_trading2`. **Grain (illustrative):** onshore + offshore farms across five zones; 96 × 15-minute intervals; ensemble members from `ECMWF`, `GFS`, `ICON`.

---

## Wind workflow

| # | Trader intent | Data / UI outcome |
|---|---|---|
| 1 | How much **wind volume** today? | `volume_forecast_silver_wind_forecast.p50_mw` aggregated to zone |
| 2 | What's the **uncertainty band**? | `p10_mw` / `p90_mw` fan |
| 3 | Which **assets / zones** drive it? | Forecast grouped by `asset_id` / `zone_code` |
| 4 | How did the forecast **move** with new NWP? | `p50_mw − prev_p50_mw` (`forecast_delta_mw`) |
| 5 | Any **curtailment / outage** risk? | `availability_pct`, `status` on summary |
| 6 | What's the **ensemble spread**? | Member dispersion in `volume_forecast_bronze_nwp_wind` |

---

## Datasets

### Dimension — `volume_forecast_dim_wind_assets`

| Column | Type | Description |
|---|---|---|
| `asset_id` | STRING | Primary key (e.g. `WIND_ON_DE_001`, `WIND_OFF_NL_001`) |
| `asset_name` | STRING | Farm label |
| `wind_type` | STRING | `ONSHORE`, `OFFSHORE` |
| `zone_code` | STRING | FK → zones |
| `nameplate_mw` | DOUBLE | Rated capacity |
| `hub_height_m` | DOUBLE | Hub height (power-curve driver) |
| `cut_in_ms` | DOUBLE | Cut-in wind speed |
| `rated_ms` | DOUBLE | Rated wind speed |
| `cut_out_ms` | DOUBLE | Cut-out wind speed |

### Bronze — `volume_forecast_bronze_nwp_wind`

NWP ensemble wind forecast — grain `forecast_ts` × `source` × `zone_code` × `interval_start`.

| Column | Type | Description |
|---|---|---|
| `ingestion_ts` | TIMESTAMP | Landing time |
| `forecast_ts` | TIMESTAMP | NWP issue time |
| `source` | STRING | `ECMWF`, `GFS`, `ICON` (ensemble member) |
| `zone_code` | STRING | FK → zones |
| `interval_start` | TIMESTAMP | Target interval |
| `wind_speed_ms` | DOUBLE | Forecast wind speed |
| `wind_direction_deg` | DOUBLE | 0–360 |
| `air_density_kgm3` | DOUBLE | Density (power yield driver) |

### Bronze — `volume_forecast_bronze_wind_scada`

Turbine telemetry — grain `telemetry_ts` × `asset_id`.

| Column | Type | Description |
|---|---|---|
| `ingestion_ts` | TIMESTAMP | Landing time |
| `telemetry_ts` | TIMESTAMP | Measurement time |
| `asset_id` | STRING | FK → wind assets |
| `actual_mw` | DOUBLE | Metered output |
| `wind_speed_ms` | DOUBLE | Nacelle-measured wind speed |
| `availability_pct` | DOUBLE | 0–100 |
| `status` | STRING | `RUNNING`, `CURTAILED`, `OUTAGE` |

### Silver — `volume_forecast_silver_wind_forecast`

Probabilistic wind generation — grain `forecast_ts` × `asset_id` × `interval_start`.

| Column | Type | Description |
|---|---|---|
| `delivery_date` | DATE | Day |
| `interval_start` | TIMESTAMP | Target interval |
| `forecast_ts` | TIMESTAMP | Forecast issue time (latest = live) |
| `asset_id` | STRING | FK → wind assets |
| `zone_code` | STRING | Denormalised zone |
| `p10_mw` | DOUBLE | 10th percentile output |
| `p50_mw` | DOUBLE | Median output |
| `p90_mw` | DOUBLE | 90th percentile output |
| `prev_p50_mw` | DOUBLE | Prior vintage P50 |
| `forecast_delta_mw` | DOUBLE | `p50_mw − prev_p50_mw` |
| `actual_mw` | DOUBLE | Metered (null for future) |

### Gold — `volume_forecast_gold_wind_summary`

Headline KPIs — grain `delivery_date` × `zone_code` × `snapshot_ts`.

| Column | Type | Description |
|---|---|---|
| `delivery_date` | DATE | Day |
| `zone_code` | STRING | FK → zones |
| `snapshot_ts` | TIMESTAMP | "As last updated" |
| `headline` | STRING | Desk-facing message |
| `total_p50_mw` | DOUBLE | Day total at P50 |
| `peak_mw` | DOUBLE | Peak generation interval |
| `band_width_mw` | DOUBLE | Mean `p90 − p10` |
| `availability_pct` | DOUBLE | Fleet availability |
| `curtailment_risk` | STRING | `LOW`, `MEDIUM`, `HIGH` |

---

## App UI (Dash) — wind generation desk

| Item | Value |
|---|---|
| **Route** | `/volume-forecasting/wind` |
| **Sidebar label** | Wind Forecasting |
| **Page module (convention)** | `app/pages/volume_forecast_wind.py` |
| **Data access** | `app/uc_pages.py` + `app/uc_sql.py`; header `sql-warehouse-dropdown` |

### Page layout

| Block | Content |
|---|---|
| **Hero** | Eyebrow, title, trader-facing summary, **Presenter guide** button |
| **Toolbar** | Date, zone, asset, onshore/offshore filter |
| **Status banner** | Day total P50, peak, band, fleet availability |
| **Outcome cards** | Total P50, peak MW, band width, curtailment risk |
| **Generation fan chart** | P10/P50/P90 by interval |
| **Asset breakdown** | P50 by asset / onshore vs offshore |
| **Forecast-move strip** | `forecast_delta_mw` with new NWP |
| **Presenter guide** | Problem → net-volume link → story → who uses |

### Presenter guide (in-app modal)

| Section | Message |
|---|---|
| What problem this solves | Wind is the biggest volume swing — forecast it probabilistically before squaring |
| How this relates to net volume | Wind P50 is the largest supply leg feeding reconciliation (07) |
| Story to tell | Day total → uncertainty fan → asset drivers → forecast move on new NWP |
| Who uses this view | Renewables desk, prompt desk, balancing |

### Widget-to-dataset binding

| UI block | Primary datasets | Key fields |
|---|---|---|
| Status banner | `volume_forecast_gold_wind_summary` | `total_p50_mw`, `peak_mw`, `band_width_mw`, `availability_pct` |
| Generation fan | `volume_forecast_silver_wind_forecast` | `interval_start`, `p10_mw`, `p50_mw`, `p90_mw` |
| Asset breakdown | `volume_forecast_silver_wind_forecast` | `asset_id`, `zone_code`, `p50_mw` |
| Forecast-move strip | `volume_forecast_silver_wind_forecast` | `interval_start`, `forecast_delta_mw` |

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
| **Upstream** | **04** shared dims; synthetic NWP ensemble + SCADA |
| **Downstream** | **07** net-volume reconciliation (supply leg); **08** scores accuracy |
| **Shared** | Owns `volume_forecast_dim_wind_assets`; consumes zones / intervals from 04 |

## Out of scope

- Real NWP vendor feeds (synthetic ensemble)
- Turbine-level wake / SCADA modelling (asset-level power curve only)
- Price / capture modelling (volume only)
- In-app mock or generated series (see [`instructions.md`](./instructions.md))
