# 06 — Solar Forecasting

> Parent brief: [`main.md`](./main.md) (Capability 06). Platform and app conventions: [`instructions.md`](./instructions.md).

## Summary

Forecast **solar PV generation** at 15-minute grain across utility-scale farms, and reconcile it with the **behind-the-meter (BTM) PV** already netted out of consumption by capability 04 — so the same rooftop kW is never double-counted. Solar drives the **midday volume surplus** and negative-price risk that the prompt desk lives with. The forecast is **probabilistic** (P10 / P50 / P90) and driven by irradiance, cloud cover, and satellite nowcasts blended against SCADA.

This is the second **supply leg** of net volume. It owns the solar asset registry, produces utility-scale generation forecasts, and explicitly carries the BTM-PV link so reconciliation (07) sums supply correctly. Data is **synthetic** but follows clear-sky / irradiance conventions.

## Databricks fit

| Capability | Role |
|---|---|
| **Structured Streaming** | Satellite nowcast + irradiance + SCADA ingest (demo materialises gold in batch) |
| **Feature Store** | Clear-sky index, cloud cover, panel temperature features |
| **MLflow** | Irradiance-to-power models; champion tracked for accuracy (08) |
| **Unity Catalog** | Governed tables; BTM-PV join with 04; semantics in [`../notebooks/uc_table_comments.py`](../notebooks/uc_table_comments.py) |

## Notebook and tables

[`../notebooks/06_solar_forecasting.ipynb`](../notebooks/06_solar_forecasting.ipynb) materialises:

| Layer | Tables |
|---|---|
| Dimension | `volume_forecast_dim_solar_assets` |
| Bronze | `volume_forecast_bronze_nwp_solar`, `volume_forecast_bronze_solar_scada` |
| Silver | `volume_forecast_silver_solar_forecast` |
| Gold | `volume_forecast_gold_solar_summary` |

Reads shared dims from **04** and joins `volume_forecast_silver_btm_pv` (04) to avoid double-counting. Owns the solar asset registry.

**Catalog.schema:** `energy_utilities.energy_trading2`. **Grain (illustrative):** utility-scale farms across five zones; 96 × 15-minute intervals; daylight intervals only carry generation.

---

## Solar workflow

| # | Trader intent | Data / UI outcome |
|---|---|---|
| 1 | How much **solar volume** today? | `volume_forecast_silver_solar_forecast.p50_mw` aggregated to zone |
| 2 | What's the **midday surplus**? | Peak `p50_mw` in `solar_window` intervals |
| 3 | What's the **uncertainty band**? | `p10_mw` / `p90_mw` fan (cloud-driven) |
| 4 | Are we **double-counting** rooftop PV? | `btm_pv_mw` reconciliation flag vs 04 |
| 5 | How does cloud cover **move** the forecast? | `forecast_delta_mw` vs prior NWP |
| 6 | **Clear-sky vs expected** today? | `clear_sky_mw` vs `p50_mw` (clear-sky index) |

---

## Datasets

### Dimension — `volume_forecast_dim_solar_assets`

| Column | Type | Description |
|---|---|---|
| `asset_id` | STRING | Primary key (e.g. `SOLAR_DE_001`) |
| `asset_name` | STRING | Farm label |
| `zone_code` | STRING | FK → zones |
| `nameplate_mw` | DOUBLE | Rated DC/AC capacity |
| `tilt_deg` | DOUBLE | Panel tilt |
| `azimuth_deg` | DOUBLE | Panel orientation |
| `tracking` | STRING | `FIXED`, `SINGLE_AXIS`, `DUAL_AXIS` |

### Bronze — `volume_forecast_bronze_nwp_solar`

Irradiance / cloud forecast — grain `forecast_ts` × `source` × `zone_code` × `interval_start`.

| Column | Type | Description |
|---|---|---|
| `ingestion_ts` | TIMESTAMP | Landing time |
| `forecast_ts` | TIMESTAMP | NWP / nowcast issue time |
| `source` | STRING | `ECMWF`, `SATELLITE_NOWCAST`, `ICON` |
| `zone_code` | STRING | FK → zones |
| `interval_start` | TIMESTAMP | Target interval |
| `ghi_wm2` | DOUBLE | Global horizontal irradiance |
| `cloud_cover_pct` | DOUBLE | 0–100 |
| `clear_sky_ghi_wm2` | DOUBLE | Theoretical clear-sky irradiance |

### Bronze — `volume_forecast_bronze_solar_scada`

Inverter telemetry — grain `telemetry_ts` × `asset_id`.

| Column | Type | Description |
|---|---|---|
| `ingestion_ts` | TIMESTAMP | Landing time |
| `telemetry_ts` | TIMESTAMP | Measurement time |
| `asset_id` | STRING | FK → solar assets |
| `actual_mw` | DOUBLE | Metered output |
| `panel_temp_c` | DOUBLE | Panel temperature (derate driver) |
| `availability_pct` | DOUBLE | 0–100 |
| `status` | STRING | `RUNNING`, `CURTAILED`, `OUTAGE` |

### Silver — `volume_forecast_silver_solar_forecast`

Probabilistic solar generation — grain `forecast_ts` × `asset_id` × `interval_start`.

| Column | Type | Description |
|---|---|---|
| `delivery_date` | DATE | Day |
| `interval_start` | TIMESTAMP | Target interval |
| `forecast_ts` | TIMESTAMP | Forecast issue time (latest = live) |
| `asset_id` | STRING | FK → solar assets |
| `zone_code` | STRING | Denormalised zone |
| `clear_sky_mw` | DOUBLE | Clear-sky theoretical output |
| `p10_mw` | DOUBLE | 10th percentile output |
| `p50_mw` | DOUBLE | Median output |
| `p90_mw` | DOUBLE | 90th percentile output |
| `prev_p50_mw` | DOUBLE | Prior vintage P50 |
| `forecast_delta_mw` | DOUBLE | `p50_mw − prev_p50_mw` |
| `actual_mw` | DOUBLE | Metered (null for future) |

### Gold — `volume_forecast_gold_solar_summary`

Headline KPIs — grain `delivery_date` × `zone_code` × `snapshot_ts`.

| Column | Type | Description |
|---|---|---|
| `delivery_date` | DATE | Day |
| `zone_code` | STRING | FK → zones |
| `snapshot_ts` | TIMESTAMP | "As last updated" |
| `headline` | STRING | Desk-facing message |
| `total_p50_mw` | DOUBLE | Day total at P50 |
| `midday_peak_mw` | DOUBLE | Peak in solar window |
| `band_width_mw` | DOUBLE | Mean `p90 − p10` |
| `btm_pv_mw` | DOUBLE | BTM PV already netted in 04 (reconciliation) |
| `negative_price_risk` | STRING | `LOW`, `MEDIUM`, `HIGH` (midday surplus) |

---

## App UI (Dash) — solar generation desk

| Item | Value |
|---|---|
| **Route** | `/volume-forecasting/solar` |
| **Sidebar label** | Solar Forecasting |
| **Page module (convention)** | `app/pages/volume_forecast_solar.py` |
| **Data access** | `app/uc_pages.py` + `app/uc_sql.py`; header `sql-warehouse-dropdown` |

### Page layout

| Block | Content |
|---|---|
| **Hero** | Eyebrow, title, trader-facing summary, **Presenter guide** button |
| **Toolbar** | Date, zone, asset filter |
| **Status banner** | Day total P50, midday peak, band, negative-price risk |
| **Outcome cards** | Total P50, midday peak, band width, BTM PV netted |
| **Generation fan chart** | P10/P50/P90 by interval with clear-sky overlay |
| **Asset breakdown** | P50 by asset |
| **BTM reconciliation strip** | Utility-scale vs BTM PV (no double count) |
| **Presenter guide** | Problem → net-volume link → story → who uses |

### Presenter guide (in-app modal)

| Section | Message |
|---|---|
| What problem this solves | Forecast midday solar surplus and negative-price risk without double-counting rooftop PV |
| How this relates to net volume | Solar P50 is the second supply leg; BTM PV reconciled with 04 |
| Story to tell | Day total → midday peak → cloud-driven band → BTM reconciliation |
| Who uses this view | Renewables desk, prompt desk, balancing |

### Widget-to-dataset binding

| UI block | Primary datasets | Key fields |
|---|---|---|
| Status banner | `volume_forecast_gold_solar_summary` | `total_p50_mw`, `midday_peak_mw`, `negative_price_risk`, `btm_pv_mw` |
| Generation fan | `volume_forecast_silver_solar_forecast` | `interval_start`, `p10_mw`, `p50_mw`, `p90_mw`, `clear_sky_mw` |
| Asset breakdown | `volume_forecast_silver_solar_forecast` | `asset_id`, `p50_mw` |
| BTM reconciliation | `volume_forecast_gold_solar_summary` + `silver_btm_pv` | `btm_pv_mw`, `total_p50_mw` |

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
| **Upstream** | **04** shared dims + `volume_forecast_silver_btm_pv`; synthetic irradiance + SCADA |
| **Downstream** | **07** net-volume reconciliation (supply leg); **08** scores accuracy |
| **Shared** | Owns `volume_forecast_dim_solar_assets`; consumes zones / intervals + BTM PV from 04 |

The BTM-PV join with 04 is load-bearing: changing 04's `volume_forecast_silver_btm_pv` grain requires coordinating with this capability and 07 to keep supply un-double-counted.

## Out of scope

- Real satellite / NWP feeds (synthetic irradiance + nowcast)
- Inverter-level derate physics (asset-level model only)
- Price / capture modelling (volume only)
- In-app mock or generated series (see [`instructions.md`](./instructions.md))
