# Short-term trading module — implementation instructions

This folder defines how to turn [`main.md`](./main.md) into a deployable **Databricks solution**: governed Delta tables in Unity Catalog, seed notebooks, and UI pages in the root [`app/`](../../../app/) Databricks App.

**Domain scope, capabilities, datasets, and desk mechanics** live only in [`main.md`](./main.md) (and the sub-specs derived from it). This file covers **repository structure, platform conventions, and delivery workflow** — do not duplicate or override domain content here.

---

## Repository layout

| Path | Purpose |
|------|---------|
| `modules/short-term/specifications/` | Product specs (this folder) |
| `modules/short-term/notebooks/` | Notebooks that materialise UC Delta tables (create when implementing) |
| `app/pages/` | Dash routes — one page (or page group) per capability |
| `app/uc_sql.py` | Statement Execution API — runs SQL on the header warehouse |
| `app/uc_pages.py` | Shared Dash helpers (`run_uc_sql`, `fq`, warehouse prompt) for capability pages |
| `resources/` | DAB bundle resources (app, and the `energy_trading_demo_data` seed job) |
| `databricks.yml` | Root bundle — deploy with `./install.sh` |

---

## Unity Catalog conventions

All short-term tables for this module use:

```text
energy_utilities.energy_trading2
```

- **Catalog:** `energy_utilities`
- **Schema:** `energy_trading2`
- **Table prefix:** `short_term_`

Override at runtime via `DEMO_UC_CATALOG`, `DEMO_UC_SCHEMA`, or `DEMO_UC_LOCATION` (see [`app/app.yaml`](../../../app/app.yaml) and [`app/uc_sql.py`](../../../app/uc_sql.py)).

Tables must be **Delta** and registered in Unity Catalog. Table schemas, medallion layers, and lineage are defined in [`main.md`](./main.md) and the per-capability sub-specifications — not in this file.

### Streaming vs batch in the demo

`main.md` frames this desk as **sub-second streaming** (Structured Streaming Real-Time Mode, Lakeflow DLT). For a **reproducible demo**, notebooks may **materialise the same gold tables in batch** — generating a fixed set of 15-minute delivery intervals for one or more trading days — while documenting the streaming pattern the production pipeline would use. App pages consume the **gold tables** identically either way. Where a table represents a live snapshot, carry a `snapshot_ts` / `forecast_ts` column so the app can show "as last updated".

### Table and column descriptions (for agents and Genie)

Each seed notebook ends with a **Unity Catalog comments** cell that runs [`../notebooks/uc_table_comments.py`](../notebooks/uc_table_comments.py). That file is the **machine-readable catalogue** of `COMMENT ON TABLE` / `COMMENT ON COLUMN` text for every `short_term_*` table. Coding agents should read `TABLE_METADATA` there (and in specs) before writing SQL or app queries. Re-run the comment cell after schema changes.

### SQL warehouse (app header)

The deployed Dash app exposes a global control in the **top header** (right side):

- **Component id:** `sql-warehouse-dropdown` (defined in [`app/app.py`](../../../app/app.py))
- **Behaviour:** lists **RUNNING** SQL warehouses in the workspace; persists the user's choice locally
- **Requirement:** every capability page callback that loads data must use `Input("sql-warehouse-dropdown", "value")` as the warehouse id passed to Statement Execution

Capability pages **must not** hard-code a warehouse id. If no warehouse is selected, show an empty state (see [`app/uc_pages.py`](../../../app/uc_pages.py) `warehouse_prompt()`).

**Query path:** header warehouse → [`run_sql`](../../../app/uc_sql.py) with `catalog` / `schema` from `DEMO_UC_CATALOG` and `DEMO_UC_SCHEMA` (same values as notebooks, set in [`app/app.yaml`](../../../app/app.yaml)).

### App pages: Unity Catalog only (no in-app dummy data)

Capability pages that show **charts, tables, KPIs, or filters driven by data** must read **only** from the module's UC schema above (`{catalog}.{schema}.short_term_*`), using [`app/uc_pages.py`](../../../app/uc_pages.py) + [`app/uc_sql.py`](../../../app/uc_sql.py) and the **SQL warehouse selected in the app header**.

| Do | Do not |
| --- | --- |
| `SELECT` from governed `short_term_*` gold/silver tables named in the sub-spec | Generate mock rows in Python (`Faker`, `random`, hard-coded lists/DataFrames) for widgets |
| Resolve catalog/schema via `DEMO_UC_CATALOG` / `DEMO_UC_SCHEMA` (same as notebooks) | Embed "sample" datasets in `app/pages/` or page modules for demos |
| Show empty states, errors, or "run `energy_trading_demo_data`" when the warehouse or tables are missing | Fall back to synthetic series so the UI "looks populated" without UC |

**Synthetic / illustrative data belongs in notebooks and jobs** that **materialise** Delta tables (e.g. `energy_trading_demo_data`). The app **consumes** those tables; it does not manufacture parallel demo data.

Presentation-only routes (e.g. overview slide decks with static copy and no SQL-backed widgets) are exempt. Any new page with **data widgets** must follow this rule.

---

## Step 1 — Expand `main.md` into sub-specifications

`main.md` is already split into **one markdown file per capability**, in this folder:

| # | File | Capability |
|---|------|------------|
| **01** | `01-trading-near-delivery.md` | Trading near delivery (squaring, imbalance, backtest) |
| **02** | `02-operations-live-dispatch.md` | 24/7 Operations & Live Dispatch (control tower + copilot) |
| **03** | `03-dsr-market-access.md` | DSR & Market Access (VPP aggregation, dispatch, settlement) |

Each sub-spec carries the **functional and data requirements** for its capability, extracted from `main.md`. Sub-specs **inherit** the global UI rules below; they do not restate them.

---

## Step 2 — Notebooks

Create seed notebooks under **`modules/short-term/notebooks/`** (one level above this folder).

Suggested naming (aligned with sub-spec numbers):

```text
01_trading_near_delivery.ipynb
02_operations_live_dispatch.ipynb
03_dsr_market_access.ipynb
```

Each notebook should:

1. Read `DEMO_UC_CATALOG` / `DEMO_UC_SCHEMA` (or the defaults above).
2. Materialise the `short_term_*` Delta tables defined in the matching sub-spec (batch generation of 15-minute intervals; document the streaming pattern).
3. Include a short introduction cell referencing that sub-spec.

**Shared dimensions** (`short_term_dim_zones`, `short_term_dim_assets`, `short_term_dim_intervals`) are owned by notebook **01** and consumed by **02** and **03** — run **01 first**.

Wire notebooks into the **Lakeflow job** `energy_trading_demo_data` in `resources/energy_trading_demo_data_job.yml` (deployed via `./install.sh`), as a branch after the schema reset. The job resets the schema first, then runs short-term notebooks **01 → 03 → 02** (control tower last because it aggregates 01 + 03). Run with:

```bash
databricks bundle run energy_trading_demo_data
```

---

## Step 3 — Databricks App UI

The root app is a **Dash** skeleton deployed as a Databricks App (`energy_trading_app`).

When adding short-term pages:

- Register routes under [`app/pages/`](../../../app/pages/) with `dash.register_page`.
- **Data pages:** query **only** Unity Catalog tables in `energy_utilities.energy_trading2` (or env overrides) via the header warehouse — no hard-coded warehouse IDs, **no in-app dummy or mock data** (see [App pages: Unity Catalog only](#app-pages-unity-catalog-only-no-in-app-dummy-data)).
- Use [`app/uc_pages.py`](../../../app/uc_pages.py): `ucp.fq("short_term_…")`, `ucp.run_uc_sql(warehouse_id, sql)`, `ucp.uc_context_strip()`, `ucp.warehouse_prompt()`.
- Bind widgets to the tables and columns named in the relevant sub-spec; column semantics are in [`../notebooks/uc_table_comments.py`](../notebooks/uc_table_comments.py).
- Use **`dcc.Loading`** around callback-driven content; match styling in [`app/assets/custom.css`](../../../app/assets/custom.css).
- Page copy and widget labels come from the sub-spec / `main.md`; put technical identifiers (table names) in footnotes where needed.

**Reference implementation:** the existing short-term pages (e.g. [`app/pages/short_term_near_delivery.py`](../../../app/pages/short_term_near_delivery.py)) — match their hero / toolbar / outcome-card / presenter-guide structure.

**Overview deck:** register a presentation-only route at `/short-term/overview` (see [`app/pages/short_term_overview.py`](../../../app/pages/short_term_overview.py) and [`app/decks/short_term.py`](../../../app/decks/short_term.py)). No SQL-backed widgets.

**Control tower (capability 02):** this page is a **live operations dashboard** rather than a single-snapshot analytics page. It still follows the UC-only rule, but is organised as the six zones in `main.md` (balance ribbon, asset dispatch, grid & frequency, market gates, event feed, copilot, alerts & shift handover). Use a single trade-date / interval selector as the "now" cursor; a refresh control re-queries the gold tables (simulating the live stream).

### Genie and natural language (capability 04)

Short-term ships a Genie Space and insights launcher mirroring long-term:

| Surface | Where it lives |
| --- | --- |
| **Genie Space** | Notebook [`04_trader_insights_genie.ipynb`](../notebooks/04_trader_insights_genie.ipynb) — title **Energy Trading Genie - Short Term**; config in [`genie_space_config.py`](../notebooks/genie_space_config.py) |
| **Insights launcher** | [`app/pages/short_term_insights.py`](../../../app/pages/short_term_insights.py) at `/short-term/insights` — lists spaces by title prefix, shows description + sample questions |
| **Metric views** | `mv_st_*` on primary gold tables (best-effort; Genie falls back to base tables) |
| **Trading copilot** | In-dash on `/short-term/control-tower` — reads `short_term_gold_copilot_recommendations` (curated; not replaced by Genie) |

Do not add in-app mock copilot text — recommendations must come from UC gold tables seeded by notebook 02.

---

## Cross-specification correlation

Each sub-spec must include a **Relationships** subsection: shared tables, upstream/downstream dependencies between capabilities, and impact when schemas change. Derive content from `main.md` — do not maintain a parallel dependency model in this file.

The control tower (**02**) is the **aggregator**: it reads squaring and imbalance outputs from **01** and DSR availability/dispatch from **03**. Breaking changes to the shared interval/zone/asset grain cascade to all three pages.

---

## Deploy and validate

From the repository root:

```bash
./install.sh                              # validate & deploy bundle
databricks bundle run energy_trading_app  # publish / update the Dash app
databricks bundle run energy_trading_demo_data
```

Before shipping a capability:

1. Sub-spec complete per `main.md` for that capability.
2. `databricks bundle run energy_trading_demo_data` succeeds; tables visible in `energy_utilities.energy_trading2`.
3. Deploy / run the app; in the **header**, select a **running SQL warehouse** that can read that schema.
4. Open the capability route (e.g. `/short-term/near-delivery`) — KPIs and charts populate from UC (not empty-state mock data).
5. App page reads **only** from documented `short_term_*` tables via `sql-warehouse-dropdown` + `run_uc_sql`.
6. Layout and loading behaviour follow the inherited UI rules below.

---

## Inherited UI rules (all short-term pages)

- **Header SQL warehouse** — all UC queries use `Input("sql-warehouse-dropdown", "value")`; never embed warehouse ids in page code.
- **Unity Catalog source of truth** — SQL-backed widgets read from `short_term_*` tables in the module schema; synthetic data is produced in notebooks/jobs, not in Dash callbacks.
- **Full-width** main content; no unnecessary narrow `max-w-*` wrappers on data widgets.
- **Consistent theme** — typography, card patterns, and chart styling from the existing app shell (match the long-term pages).
- **Loading states** — show a spinner while SQL callbacks run; hide on success or error.
- **Demo disclaimer** — where `main.md` or the sub-spec marks data as illustrative, say so on the page.
- **No auto-refresh polling** — a manual refresh control re-queries the gold tables; do not add background intervals that poll the warehouse continuously.

---

*Parent brief: [`main.md`](./main.md). Root app and bundle: [`README.md`](../../../README.md).*
