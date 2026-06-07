# 04 — Smart Metering

> Parent brief: [`main.md`](./main.md) (Capability 04). Platform and app conventions: [`instructions.md`](./instructions.md).

## Summary

Smart metering is the **data-engineering backbone** of the module. Millions of AMI meters emit high-cardinality, late-arriving, sometimes-corrupt interval reads. This capability ingests them, validates quality, **deducts behind-the-meter (BTM) PV**, and rolls individual meters up into governed, **forecast-ready load profiles** by customer segment, tariff, and zone — under Unity Catalog access controls because household reads are **personal data (GDPR)**.

This capability owns the module's **shared dimensions** — `volume_forecast_dim_zones`, `volume_forecast_dim_segments`, `volume_forecast_dim_intervals` — and the curated `volume_forecast_silver_meter_profile` that every consumption capability (01, 02, 03) reads. Data is **synthetic** but follows AMI conventions (interval cadence, meter events, gaps). Build this notebook **first**.

## Databricks fit

| Capability | Role |
|---|---|
| **Auto Loader / Structured Streaming** | High-cardinality, incremental ingest of AMI interval files |
| **Lakeflow Declarative Pipelines (DLT)** | Bronze → silver → gold profiling with expectations |
| **Lakehouse Monitoring** | Data-quality SLAs: completeness, lateness, corrupt-read rate |
| **Unity Catalog (masking / RLS)** | Consent-aware aggregation; no individual meter exposed downstream |
| **Delta** | Governed profile tables; semantics in [`../notebooks/uc_table_comments.py`](../notebooks/uc_table_comments.py) |

## Notebook and tables

[`../notebooks/04_smart_metering.ipynb`](../notebooks/04_smart_metering.ipynb) materialises:

| Layer | Tables |
|---|---|
| Dimensions (shared) | `volume_forecast_dim_zones`, `volume_forecast_dim_segments`, `volume_forecast_dim_intervals` |
| Bronze | `volume_forecast_bronze_meter_reads`, `volume_forecast_bronze_meter_events` |
| Silver | `volume_forecast_silver_btm_pv`, `volume_forecast_silver_meter_profile` |
| Gold | `volume_forecast_gold_metering_quality` |

**Catalog.schema:** `energy_utilities.energy_trading2` (override with `DEMO_UC_CATALOG` / `DEMO_UC_SCHEMA`). Seed job: `energy_trading_demo_data` (run notebook **04 first** — it owns the shared dimensions and curated profiles).

**Grain (illustrative):** AMI reads aggregated to **15-minute intervals**; five zones (`DE`, `NL`, `FR`, `BE`, `AT`); customer segments (`RES`, `RES_PV`, `RES_EV`, `SME`, `CNI`). Individual meters are synthetic and **never surfaced** below the segment/zone aggregate.

---

## Smart-metering workflow

The **Dash capability page** mirrors this sequence. Each step maps to gold/silver tables — no in-app synthetic data.

| # | Operator intent | Data / UI outcome |
|---|---|---|
| 1 | Is the meter feed **complete** right now? | `volume_forecast_gold_metering_quality.completeness_pct` per zone/segment |
| 2 | How **late / corrupt** are the reads? | `late_read_pct`, `corrupt_read_pct`, `dq_status` |
| 3 | What is the **net load profile** by segment? | `volume_forecast_silver_meter_profile.net_load_mw` (gross − BTM PV) |
| 4 | How much **BTM PV** are we deducting? | `volume_forecast_silver_btm_pv.btm_pv_mw` per zone/interval |
| 5 | Which **segments** drive the zone total? | Profile grouped by `segment_code` |
| 6 | Can a forecast **trust** this vintage? | `profile_version`, `as_of_ts`, `dq_status` gate downstream reads |

**Quality gate (illustrative):** a profile interval is `GOOD` when `completeness_pct ≥ 98` and `corrupt_read_pct ≤ 1`; otherwise `IMPUTED` (gap-filled) or `SUSPECT` (held back from consumption forecasts).

---

## Datasets

### `volume_forecast_dim_zones`

Shared dimension — one row per bidding zone (owned here; used by 01–03, 05–08).

| Column | Type | Description |
|---|---|---|
| `zone_code` | STRING | Primary key: `DE`, `NL`, `FR`, `BE`, `AT` |
| `country` | STRING | Country name |
| `tso_name` | STRING | Transmission System Operator |
| `control_area` | STRING | TSO control / imbalance area label |
| `eic_code` | STRING | Illustrative EIC identifier |
| `currency` | STRING | `EUR` |

### `volume_forecast_dim_segments`

Shared dimension — customer segments behind the meter (owned here; used by 01, 02).

| Column | Type | Description |
|---|---|---|
| `segment_code` | STRING | Primary key: `RES`, `RES_PV`, `RES_EV`, `SME`, `CNI` |
| `segment_name` | STRING | Human label (e.g. "Residential with rooftop PV") |
| `customer_class` | STRING | `RESIDENTIAL`, `COMMERCIAL`, `INDUSTRIAL` |
| `has_btm_pv` | BOOLEAN | Segment carries behind-the-meter solar |
| `has_ev` | BOOLEAN | Segment carries EV charging load |
| `default_tariff` | STRING | Illustrative tariff profile code |

### `volume_forecast_dim_intervals`

Shared time spine — one row per 15-minute interval (owned here; used across the module).

| Column | Type | Description |
|---|---|---|
| `delivery_date` | DATE | Calendar / delivery day |
| `interval_start` | TIMESTAMP | Interval start (15-min grain) |
| `interval_end` | TIMESTAMP | Interval end |
| `interval_index` | INT | 1–96 within the day |
| `hour` | INT | 0–23 |
| `day_type` | STRING | `WEEKDAY`, `WEEKEND`, `HOLIDAY` |
| `season` | STRING | `WINTER`, `SPRING`, `SUMMER`, `AUTUMN` |
| `is_peak` | BOOLEAN | Peak-load window flag |
| `solar_window` | BOOLEAN | Midday solar-peak flag |

### Bronze — raw landing

#### `volume_forecast_bronze_meter_reads`

Raw AMI interval reads — grain `read_ts` × `meter_id` (synthetic; aggregated upward, never exposed).

| Column | Type | Description |
|---|---|---|
| `ingestion_ts` | TIMESTAMP | Landing time (Auto Loader) |
| `read_ts` | TIMESTAMP | Interval the read covers |
| `meter_id` | STRING | Synthetic surrogate meter id |
| `segment_code` | STRING | FK → segments |
| `zone_code` | STRING | FK → zones |
| `consumption_kwh` | DOUBLE | Imported energy in the interval |
| `export_kwh` | DOUBLE | Exported (BTM PV) energy |
| `read_quality` | STRING | `OK`, `ESTIMATED`, `MISSING`, `CORRUPT` |

#### `volume_forecast_bronze_meter_events`

Meter lifecycle / data events — grain `event_ts` × `meter_id`.

| Column | Type | Description |
|---|---|---|
| `ingestion_ts` | TIMESTAMP | Landing time |
| `event_ts` | TIMESTAMP | Event time |
| `meter_id` | STRING | Synthetic meter id |
| `event_type` | STRING | `GAP`, `LATE`, `TAMPER`, `RECONNECT`, `FW_UPDATE` |
| `detail` | STRING | Free-text note |

### Silver — conformed

#### `volume_forecast_silver_btm_pv`

Behind-the-meter PV deducted from gross consumption — grain `interval_start` × `zone_code` × `segment_code`.

| Column | Type | Description |
|---|---|---|
| `delivery_date` | DATE | Day |
| `interval_start` | TIMESTAMP | Interval |
| `zone_code` | STRING | FK → zones |
| `segment_code` | STRING | FK → segments |
| `btm_pv_mw` | DOUBLE | Estimated BTM PV generation (deducted from gross) |
| `n_pv_meters` | LONG | Meters with export in the interval |

#### `volume_forecast_silver_meter_profile`

**Curated, forecast-ready net load profile** — grain `interval_start` × `zone_code` × `segment_code`. The shared input to capabilities 01–03.

| Column | Type | Description |
|---|---|---|
| `delivery_date` | DATE | Day |
| `interval_start` | TIMESTAMP | Interval |
| `zone_code` | STRING | FK → zones |
| `segment_code` | STRING | FK → segments |
| `gross_load_mw` | DOUBLE | Total imported demand |
| `btm_pv_mw` | DOUBLE | BTM PV deducted |
| `net_load_mw` | DOUBLE | `gross_load_mw − btm_pv_mw` |
| `n_meters` | LONG | Meters aggregated (privacy: never < k-anonymity threshold) |
| `dq_status` | STRING | `GOOD`, `IMPUTED`, `SUSPECT` |
| `profile_version` | INT | Curation version |
| `as_of_ts` | TIMESTAMP | When the profile was curated |

### Gold — quality

#### `volume_forecast_gold_metering_quality`

Data-quality SLA rollup — grain `delivery_date` × `zone_code` × `segment_code`.

| Column | Type | Description |
|---|---|---|
| `delivery_date` | DATE | Day |
| `zone_code` | STRING | FK → zones |
| `segment_code` | STRING | FK → segments |
| `expected_reads` | LONG | Meters × intervals expected |
| `received_reads` | LONG | Reads actually landed |
| `completeness_pct` | DOUBLE | `received / expected × 100` |
| `late_read_pct` | DOUBLE | % arriving after the interval closed |
| `corrupt_read_pct` | DOUBLE | % flagged `CORRUPT` / `MISSING` |
| `imputed_intervals` | LONG | Intervals gap-filled |
| `dq_status` | STRING | `GOOD`, `WATCH`, `BREACH` |

---

## App UI (Dash) — smart-metering operations

Implements the [smart-metering workflow](#smart-metering-workflow). Inherits global app rules from [`instructions.md`](./instructions.md) (header warehouse, no in-app mock series, loading states, full-width layout).

| Item | Value |
|---|---|
| **Route** | `/volume-forecasting/smart-metering` |
| **Sidebar label** | Smart Metering |
| **Page module (convention)** | `app/pages/volume_forecast_smart_metering.py` |
| **Data access** | `app/uc_pages.py` + `app/uc_sql.py`; header `sql-warehouse-dropdown`; datasets in this spec |

### Page layout

| Block | Content |
|---|---|
| **Hero** | Eyebrow, title, trader/operator summary, **Presenter guide** button |
| **Toolbar** | Date, zone, segment filter, refresh |
| **Status banner** | Feed completeness, late/corrupt %, profile version & as-of |
| **Outcome cards** | Completeness %, corrupt %, imputed intervals, BTM PV deducted |
| **Net load profile chart** | `net_load_mw` by interval, stacked by segment |
| **BTM PV strip** | `btm_pv_mw` overlaid on gross load |
| **Quality grid** | Per zone/segment completeness, lateness, dq_status |
| **Footnote** | Synthetic meters; aggregated above k-anonymity; illustrative |
| **Presenter guide** | Problem → why governance/privacy → story → who uses |

### Presenter guide (in-app modal)

| Section | Message |
|---|---|
| What problem this solves | Turn millions of messy meter reads into one clean, trusted, privacy-safe load profile |
| Why it matters | Every consumption forecast (01–03) is only as good as this profile; bad data → bad volumes → cash-out |
| Governance & privacy | Household data is personal — aggregated above a k-threshold, access-controlled in Unity Catalog |
| Story to tell | Feed completeness → deduct rooftop PV → net load by segment → trusted profile version |
| Who uses this view | Metering operations, forecasting analysts, data governance |

### Empty and error states

| Condition | Message / behaviour |
|---|---|
| No warehouse selected | Prompt to select a running warehouse (no mock data) |
| Warehouse selected, no data | Prompt to run `energy_trading_demo_data`, then retry |
| Query failure | Show error text; do not fabricate charts |

### Widget-to-dataset binding

| UI block | Primary datasets | Key fields |
|---|---|---|
| Status banner | `volume_forecast_gold_metering_quality` | `completeness_pct`, `late_read_pct`, `corrupt_read_pct`, `dq_status` |
| Outcome cards | `volume_forecast_gold_metering_quality` + `silver_btm_pv` | `completeness_pct`, `corrupt_read_pct`, `imputed_intervals`, `btm_pv_mw` |
| Net load profile | `volume_forecast_silver_meter_profile` | `interval_start`, `segment_code`, `net_load_mw` |
| BTM PV strip | `volume_forecast_silver_btm_pv` | `interval_start`, `btm_pv_mw` |
| Quality grid | `volume_forecast_gold_metering_quality` | `zone_code`, `segment_code`, `completeness_pct`, `dq_status` |

---

## Relationships

| Direction | Dependency |
|---|---|
| **Upstream** | Synthetic AMI reads + meter events (API-shaped); no module dependency |
| **Downstream** | **01, 02, 03** read `volume_forecast_silver_meter_profile`; everything reads the shared dims |
| **Shared** | Owns `volume_forecast_dim_zones`, `volume_forecast_dim_segments`, `volume_forecast_dim_intervals` |

Schema or grain changes to the shared dimensions or to `volume_forecast_silver_meter_profile` require coordination with all consumption capability owners. Run **04 first** in the seed job.

## Out of scope

- Real AMI head-end / MDM integration (synthetic reads only)
- Individual-meter exposure in the app (aggregates only; k-anonymity enforced)
- True streaming ingest in the demo (batch materialisation; streaming pattern documented)
- Real GDPR consent workflow (illustrative access-control pattern only)
- In-app mock or generated series (see [`instructions.md`](./instructions.md))
