# Volume forecasting module — implementation instructions

This folder defines how to turn [`main.md`](./main.md) into a deployable **Databricks solution**: governed Delta tables in Unity Catalog, seed notebooks, and UI pages in the root [`app/`](../../../app/) Databricks App.

**Domain scope, capabilities, datasets, and desk mechanics** live only in [`main.md`](./main.md). This file covers **repository structure, platform conventions, and delivery workflow** — do not duplicate or override domain content here.

---

## Repository layout

| Path | Purpose |
|------|---------|
| `modules/volume-forecasting/specifications/` | Product specs (this folder) |
| `modules/volume-forecasting/notebooks/` | Notebooks that materialise UC Delta tables (planned `01` → `08`) |
| `app/pages/` | Dash routes — one page per capability |
| `app/decks/` | Overview slide decks (`volume_forecast.py`, `volume_forecast_architecture.py`) |
| `app/uc_sql.py` | Statement Execution API — runs SQL on the header warehouse |
| `app/uc_pages.py` | Shared Dash helpers (`run_uc_sql`, `fq`, warehouse prompt) for capability pages |
| `resources/` | DAB bundle resources (app, and the `energy_trading_demo_data` seed job) |
| `databricks.yml` | Root bundle — deploy with `./install.sh` |

---

## Unity Catalog conventions

All volume-forecasting tables for this module use:

```text
energy_utilities.energy_trading2
```

- **Catalog:** `energy_utilities`
- **Schema:** `energy_trading2`
- **Table prefix:** `volume_forecast_`

Override at runtime via `DEMO_UC_CATALOG`, `DEMO_UC_SCHEMA`, or `DEMO_UC_LOCATION` (see [`app/app.yaml`](../../../app/app.yaml) and [`app/uc_sql.py`](../../../app/uc_sql.py)).

Tables must be **Delta** and registered in Unity Catalog. Table schemas, medallion layers, and lineage are defined in [`main.md`](./main.md) — not in this file.

### Batch vs streaming in the demo

`main.md` frames forecasting as **continuous re-forecast** (weather + SCADA updates). For a **reproducible demo**, notebooks may **materialise the same gold tables in batch** — generating a fixed set of 15-minute intervals and multiple `forecast_ts` versions — while documenting the streaming pattern production would use. App pages consume the **gold tables** identically either way. Carry `forecast_ts`, `as_of_ts`, and `publication_status` on publish tables.

### Table and column descriptions (for agents and Genie)

Each seed notebook ends with a **Unity Catalog comments** cell that runs [`../notebooks/uc_table_comments.py`](../notebooks/uc_table_comments.py). Coding agents should read `TABLE_METADATA` there before writing SQL or app queries. Re-run the comment cell after schema changes.

### SQL warehouse (app header)

The deployed Dash app exposes a global control in the **top header** (right side):

- **Component id:** `sql-warehouse-dropdown` (defined in [`app/app.py`](../../../app/app.py))
- **Behaviour:** lists **RUNNING** SQL warehouses in the workspace; persists the user's choice locally
- **Requirement:** every capability page callback that loads data must use `Input("sql-warehouse-dropdown", "value")` as the warehouse id passed to Statement Execution

Capability pages **must not** hard-code a warehouse id. If no warehouse is selected, show an empty state (see [`app/uc_pages.py`](../../../app/uc_pages.py) `warehouse_prompt()`).

### App pages: Unity Catalog only (no in-app dummy data)

Capability pages that show **charts, tables, KPIs, or filters driven by data** must read **only** from the module's UC schema above (`{catalog}.{schema}.volume_forecast_*`), using [`app/uc_pages.py`](../../../app/uc_pages.py) + [`app/uc_sql.py`](../../../app/uc_sql.py) and the **SQL warehouse selected in the app header**.

| Do | Do not |
| --- | --- |
| `SELECT` from governed `volume_forecast_*` gold/silver tables named in `main.md` | Generate mock rows in Python for widgets |
| Resolve catalog/schema via `DEMO_UC_CATALOG` / `DEMO_UC_SCHEMA` | Embed sample datasets in `app/pages/` |
| Show empty states when warehouse or tables are missing | Fall back to synthetic series in the app |

**Synthetic / illustrative data belongs in notebooks and jobs** that materialise Delta tables. The app **consumes** those tables.

Presentation-only routes (overview slide decks) are exempt.

---

## Step 1 — Expand `main.md` into sub-specifications

`main.md` is split into **one markdown file per capability**, in this folder:

| # | File | Capability |
|---|------|------------|
| **01** | `01-customer-consumption-short-term.md` | Customer Consumption · Short Term |
| **02** | `02-customer-consumption-long-term.md` | Customer Consumption · Long Term |
| **03** | `03-industry-involvement.md` | Industry Involvement (baseline + flexibility) |
| **04** | `04-smart-metering.md` | Smart Metering (owns shared dims + curated profile) |
| **05** | `05-wind-forecasting.md` | Wind Forecasting (owns wind asset registry) |
| **06** | `06-solar-forecasting.md` | Solar Forecasting (owns solar asset registry; BTM PV reconciliation) |
| **07** | `07-publication-net-volume.md` | Publication & Net-Volume Reconciliation (official source of truth) |
| **08** | `08-forecast-accuracy-value.md` | Forecast Accuracy & Value (error → euros, model governance) |

Each sub-spec carries the **functional and data requirements** for its capability, extracted from `main.md`. Sub-specs **inherit** the global UI rules below; they do not restate them.

---

## Step 2 — Notebooks

Implemented under `modules/volume-forecasting/notebooks/` (see the [notebooks README](../notebooks/README.md)). Smart metering (04) is the data backbone — it materialises the curated profile and shared dimensions the consumption capabilities read, so it runs first. Publication (07) reconciles demand + generation, so it runs after the legs; accuracy (08) scores published output, so it runs last. Each notebook applies its UC comments from [`uc_table_comments.py`](../notebooks/uc_table_comments.py) in the final cell.

| Notebook | Capability | Depends on |
|---|---|---|
| `04_smart_metering.ipynb` | 04 Smart Metering | — (owns shared dims + curated meter profile) |
| `01_consumption_short_term.ipynb` | 01 Customer Consumption · Short Term | 04 (reads meter profile) |
| `02_consumption_long_term.ipynb` | 02 Customer Consumption · Long Term | 04 (reads historical profile baseline) |
| `03_industry_involvement.ipynb` | 03 Industry Involvement | — (owns industrial site dim) |
| `05_wind_forecasting.ipynb` | 05 Wind Forecasting | — (owns wind asset registry) |
| `06_solar_forecasting.ipynb` | 06 Solar Forecasting | 04 (BTM-PV reconciliation), owns solar asset registry |
| `07_publication_net_volume.ipynb` | 07 Publication & Net-Volume Reconciliation | 01, 03, 05, 06 |
| `08_forecast_accuracy_value.ipynb` | 08 Forecast Accuracy & Value | 07 |

Notebook **04** owns shared dimensions: `volume_forecast_dim_zones`, `volume_forecast_dim_segments`, `volume_forecast_dim_intervals`, plus curated `volume_forecast_silver_meter_profile`. Notebook **05** owns `volume_forecast_dim_wind_assets`; **06** owns `volume_forecast_dim_solar_assets`; **03** owns `volume_forecast_dim_industrial_sites`. Run order: **04 → (01, 02, 06 after 04) ; (03, 05) → 07 (reconcile/publish) → 08 (accuracy)** — wired in `resources/energy_trading_demo_data_job.yml`.

---

## Step 3 — App pages

| Route | Page module | Status |
|---|---|---|
| `/volume-forecasting/overview` | `app/pages/volume_forecast_overview.py` | **Implemented** (presentation deck) |
| `/volume-forecasting/consumption-short-term` | `app/pages/volume_forecast_consumption_short_term.py` | **Implemented** (01) |
| `/volume-forecasting/consumption-long-term` | `app/pages/volume_forecast_consumption_long_term.py` | **Implemented** (02) |
| `/volume-forecasting/industry` | `app/pages/volume_forecast_industry.py` | **Implemented** (03) |
| `/volume-forecasting/smart-metering` | `app/pages/volume_forecast_smart_metering.py` | **Implemented** (04) |
| `/volume-forecasting/wind` | `app/pages/volume_forecast_wind.py` | **Implemented** (05) |
| `/volume-forecasting/solar` | `app/pages/volume_forecast_solar.py` | **Implemented** (06) |
| `/volume-forecasting/publication` | `app/pages/volume_forecast_publication.py` | **Implemented** (07) |
| `/volume-forecasting/accuracy` | `app/pages/volume_forecast_accuracy.py` | **Implemented** (08) |

All capability routes above are data-backed Dash pages (UC SQL via `uc_pages.run_uc_sql`). Overview uses the presentation deck; 01–08 follow each sub-spec layout.

Register new pages in [`app/app.py`](../../../app/app.py) (`PAGE_MODULES` and `VALID_PATHS`).

Inherited UI rules from short-term:

- `capability_section()` for widget blocks with trader-facing descriptions
- `presenter_tip_button()` + `presenter_modal()` for presenter guides (business tone)
- `hero_title()` + Lucide icons via [`app/ui_icons.py`](../../../app/ui_icons.py)

---

## Step 4 — Bundle job (when notebooks exist)

Extend [`resources/energy_trading_demo_data_job.yml`](../../../resources/energy_trading_demo_data_job.yml) with `vf04` (smart metering) first, then `vf01` / `vf02` / `vf03` (consumption) and `vf05` / `vf06` (wind, solar) in parallel, then `vf07` (publish/reconcile), then `vf08` (accuracy). Run order: **04 → (01, 02, 03) + (05, 06) → 07 → 08**.

Update [`modules/setup/00_reset_demo_schema.ipynb`](../setup/00_reset_demo_schema.ipynb) schema comment to mention `volume_forecast_*`.

---

## Step 5 — Validate

1. `databricks bundle validate`
2. `databricks bundle run energy_trading_demo_data` (after job tasks added)
3. `databricks bundle run energy_trading_app`
4. Open `/volume-forecasting/overview` and each capability route with a warehouse selected

---

## Cross-module lineage

| This module produces | Consumed by |
|---|---|
| **Published net volume (07)** per interval | Short-term squaring (`short_term` net-position / squaring widgets) — the single source of truth |
| Long-term consumption load shapes (02) + renewable volume profiles (05, 06) | Long-term curve / origination hedge sizing and PPA / cannibalization models |
| Industrial demand-side flexibility (03) | Short-term DSR & market access bid-stack aggregation |
| Forecast accuracy & cost-of-error (08) | Risk / management model governance and commercial reporting |
| Curated meter profiles (04) | Internal input to consumption capabilities 01–03 |
| Wind (05) + solar (06) ensembles | Internal input to net-volume reconciliation (07) |

Trading desks read the **published** net volume (07), not the raw capability outputs. Document handoff columns in the producing notebook and `uc_table_comments.py` when implementing.

---

*Parent brief: [`../short-term/specifications/main.md`](../short-term/specifications/main.md).*
