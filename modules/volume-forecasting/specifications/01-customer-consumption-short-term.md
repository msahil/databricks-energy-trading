# 01 — Customer Consumption · Short Term

> Parent brief: [`main.md`](./main.md) (Capability 01). Platform and app conventions: [`instructions.md`](./instructions.md).

## Summary

Forecast retail and commercial demand from **now through the next several days** (rolling horizon: 2 settled history days, today, 2 forecast days) at 15-minute grain. The forecast starts from the **latest curated meter profile** (climatological load) from capability 04 and is **shaped by weather** — a per-zone temperature anomaly vs the seasonal normal moves demand, scaled by each segment's weather sensitivity. The forecast is **probabilistic** — P10 / P50 / P90 per interval, with the band widening by lead time — because the prompt desk squares against P50 but sizes risk against the band. Each interval carries **two forecast vintages** (the previous run and the latest run) so the desk can see how the number moved; settled intervals also carry the realised `actual_mw` for backtesting (08).

This is the **load number the short-term prompt desk squares against**. It reads the shared dimensions and `volume_forecast_silver_meter_profile` (owned by 04) and publishes a per-segment, per-zone short-horizon forecast that feeds net-volume reconciliation (07). Data is **synthetic** but follows demand-forecasting conventions.

## Databricks fit

| Capability | Role |
|---|---|
| **Structured Streaming** | Live meter + weather ingest (demo materialises the same gold in batch) |
| **Feature Store** | Weather + calendar + lagged-load features, reused across vintages |
| **MLflow** | Short-horizon load models; champion tracked for accuracy (08) |
| **Delta** | Governed forecast tables; semantics in [`../notebooks/uc_table_comments.py`](../notebooks/uc_table_comments.py) |

## Notebook and tables

[`../notebooks/01_consumption_short_term.ipynb`](../notebooks/01_consumption_short_term.ipynb) materialises:

| Layer | Tables |
|---|---|
| Bronze | `volume_forecast_bronze_weather_obs` |
| Silver | `volume_forecast_silver_consumption_st` |
| Gold | `volume_forecast_gold_consumption_st_summary` |

Reads shared dims + `volume_forecast_silver_meter_profile` from **04** (run 04 first).

**Catalog.schema:** `energy_utilities.energy_trading2`. **Grain (illustrative):** rolling horizon of `delivery_date`s × 96 intervals; five zones; segments from `volume_forecast_dim_segments`. The latest `forecast_ts` per interval is the live forecast; earlier ones support accuracy backtesting (08).

---

## Short-term consumption workflow

| # | Trader intent | Data / UI outcome |
|---|---|---|
| 1 | How much will my book consume **this afternoon / tomorrow**? | `volume_forecast_silver_consumption_st.p50_mw` by interval |
| 2 | What's the **uncertainty band**? | `p10_mw` / `p90_mw` fan around P50 |
| 3 | Which **segments** drive the load? | Forecast grouped by `segment_code` |
| 4 | How did the forecast **move** since last run? | `p50_mw − prev_p50_mw` (`forecast_delta_mw`) |
| 5 | What's the **headline** for the desk? | `volume_forecast_gold_consumption_st_summary.headline`, `peak_mw`, `peak_interval` |
| 6 | Is the profile **trustworthy**? | `dq_status` carried from 04's meter profile |

---

## Datasets

### Bronze — `volume_forecast_bronze_weather_obs`

Weather drivers — grain `forecast_ts` × `zone_code` × `interval_start`.

| Column | Type | Description |
|---|---|---|
| `ingestion_ts` | TIMESTAMP | Landing time |
| `forecast_ts` | TIMESTAMP | Weather forecast issue time |
| `source` | STRING | `ECMWF`, `GFS`, `ICON`, `VENDOR_X` |
| `zone_code` | STRING | FK → zones |
| `interval_start` | TIMESTAMP | Target interval |
| `temperature_c` | DOUBLE | Forecast temperature |
| `solar_irradiance_wm2` | DOUBLE | Forecast irradiance (BTM PV driver) |
| `cloud_cover_pct` | DOUBLE | 0–100 |

### Silver — `volume_forecast_silver_consumption_st`

Probabilistic short-term consumption — grain `forecast_ts` × `zone_code` × `segment_code` × `interval_start`.

| Column | Type | Description |
|---|---|---|
| `delivery_date` | DATE | Day |
| `interval_start` | TIMESTAMP | Target interval |
| `forecast_ts` | TIMESTAMP | Forecast **run** time — two vintages per interval (prev run + latest run); latest = live |
| `zone_code` | STRING | FK → zones |
| `segment_code` | STRING | FK → segments |
| `p10_mw` | DOUBLE | 10th percentile demand (band widens with lead time) |
| `p50_mw` | DOUBLE | Median demand (squaring reference) |
| `p90_mw` | DOUBLE | 90th percentile demand (band widens with lead time) |
| `prev_p50_mw` | DOUBLE | Prior-run P50 for this interval (null on the prev-run row) |
| `forecast_delta_mw` | DOUBLE | `p50_mw − prev_p50_mw` (null on the prev-run row) |
| `temperature_c` | DOUBLE | Driver temperature, joined from `volume_forecast_bronze_weather_obs` |
| `actual_mw` | DOUBLE | Realised demand on settled intervals (profile × full weather response); null in the future |
| `dq_status` | STRING | Carried from meter profile (`GOOD`/`IMPUTED`/`SUSPECT`) |

### Gold — `volume_forecast_gold_consumption_st_summary`

Headline KPIs — grain `delivery_date` × `zone_code` × `snapshot_ts`.

| Column | Type | Description |
|---|---|---|
| `delivery_date` | DATE | Day |
| `zone_code` | STRING | FK → zones |
| `snapshot_ts` | TIMESTAMP | "As last updated" |
| `headline` | STRING | Desk-facing summary message |
| `avg_demand_mw` | DOUBLE | Mean instantaneous P50 demand across the day (MW) |
| `total_demand_mwh` | DOUBLE | Daily energy at P50 = `sum(p50_mw) × 0.25h` (MWh) |
| `peak_mw` | DOUBLE | Peak interval demand |
| `peak_interval` | TIMESTAMP | When peak occurs |
| `band_width_mw` | DOUBLE | Mean `p90 − p10` (uncertainty) |
| `dq_status` | STRING | Worst dq_status feeding the day |

---

## App UI (Dash) — short-term consumption desk

| Item | Value |
|---|---|
| **Route** | `/volume-forecasting/consumption-short-term` |
| **Sidebar label** | Customer Consumption — Short Term |
| **Page module (convention)** | `app/pages/volume_forecast_consumption_short_term.py` |
| **Data access** | `app/uc_pages.py` + `app/uc_sql.py`; header `sql-warehouse-dropdown` |

### Page layout

| Block | Content |
|---|---|
| **Hero** | Eyebrow, title, trader-facing summary, **Presenter guide** button |
| **Toolbar** | Date, zone, segment filter, refresh |
| **Status banner** | Day total P50, peak MW & time, uncertainty band, dq status |
| **Outcome cards** | Daily energy (MWh), peak, band width, forecast move since last run |
| **Demand fan chart** | P10/P50/P90 by interval, with realised `actual_mw` overlaid up to "now" |
| **Segment breakdown** | P50 stacked by segment |
| **Forecast-move strip** | `forecast_delta_mw` by interval |
| **Footnote** | Selected date only; synthetic; reads curated 04 profile |
| **Presenter guide** | Problem → squaring link → story → who uses |

### Presenter guide (in-app modal)

| Section | Message |
|---|---|
| What problem this solves | Know how much customers will draw before the prompt desk squares |
| How this relates to squaring | P50 is the demand leg of net position; band sizes the risk |
| Story to tell | Day shape → uncertainty band → segment drivers → forecast move |
| Who uses this view | Short-term traders, schedulers |

### Widget-to-dataset binding

| UI block | Primary datasets | Key fields |
|---|---|---|
| Status banner | `volume_forecast_gold_consumption_st_summary` | `total_demand_mwh`, `avg_demand_mw`, `peak_mw`, `band_width_mw`, `dq_status` |
| Demand fan | `volume_forecast_silver_consumption_st` | `interval_start`, `p10_mw`, `p50_mw`, `p90_mw`, `actual_mw` (latest `forecast_ts`) |
| Segment breakdown | `volume_forecast_silver_consumption_st` | `segment_code`, `p50_mw` |
| Forecast-move strip | `volume_forecast_silver_consumption_st` | `interval_start`, `forecast_delta_mw` |

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
| **Upstream** | **04** curated `volume_forecast_silver_meter_profile`; shared dims; weather bronze |
| **Downstream** | **07** net-volume reconciliation consumes the demand leg; **08** scores accuracy |
| **Shared** | Consumes dims owned by 04 |

## Out of scope

- Real retail metering / settlement integration (synthetic)
- True streaming in the demo (batch materialisation; streaming documented)
- Tariff-level revenue modelling
- In-app mock or generated series (see [`instructions.md`](./instructions.md))
