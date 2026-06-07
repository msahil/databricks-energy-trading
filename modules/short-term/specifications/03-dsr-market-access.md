# 03 — DSR & Market Access

> Parent brief: [`main.md`](./main.md) (Capability 3). Platform and app conventions: [`instructions.md`](./instructions.md).

## Summary

Demand-Side Response (DSR) and Market Access turn thousands of small, distributed flexible assets — industrial loads, EV depots, heat pumps, behind-the-meter batteries — into a single tradable **virtual power plant (VPP)**. The desk **ingests** high-cardinality submeter telemetry, computes each asset's **counterfactual baseline** and **available flexibility**, **aggregates** assets into **prequalified bid stacks** for wholesale Intraday and TSO balancing (aFRR/mFRR), **dispatches** the optimal subset against price/grid signals, **verifies** delivered response, and **settles** realized value back to each third-party owner via **Unity Catalog / Delta Sharing**.

It consumes the shared dimensions from [`01-trading-near-delivery.md`](./01-trading-near-delivery.md) and feeds its dispatch contribution into the [control tower](./02-operations-live-dispatch.md) balance ribbon. Data is **illustrative** but follows aggregator/VPP conventions.

## Databricks fit

| Capability | Role |
|---|---|
| **Lakeflow / Structured Streaming** | High-cardinality submeter ingest (thousands of assets); demo materialises gold in batch |
| **Mosaic AI** | Per-asset baseline + available-flexibility forecasting |
| **Spark** | Bid-stack aggregation and dispatch optimization across the fleet |
| **Unity Catalog + Delta Sharing** | Multi-tenant governance; per-owner settlement shared securely to asset owners |
| **Genie / AI-BI** | Flexibility availability and settlement Q&A |

## Notebook and tables

[`../notebooks/03_dsr_market_access.ipynb`](../notebooks/03_dsr_market_access.ipynb) materialises:

| Layer | Tables |
|---|---|
| Inputs (capability 01) | `short_term_dim_zones`, `short_term_dim_intervals` |
| Registry | `short_term_dim_dsr_assets`, `short_term_dim_dsr_owners` |
| Bronze | `short_term_bronze_submeter_telemetry` |
| Silver | `short_term_silver_dsr_availability` |
| Gold — market access | `short_term_gold_dsr_bid_stack`, `short_term_gold_dsr_dispatch`, `short_term_gold_dsr_settlement` |
| Gold — summary | `short_term_gold_dsr_summary` |

**Catalog.schema:** `energy_utilities.energy_trading2` (override with `DEMO_UC_CATALOG` / `DEMO_UC_SCHEMA`). Seed job: `energy_trading_demo_data` (run notebook **01 before 03** — shared dimensions).

**Fleet (illustrative):** a **150 MW aggregated portfolio** of a few hundred sampled assets across types (`INDUSTRIAL_LOAD`, `EV_DEPOT`, `HEAT_PUMP`, `BTM_BATTERY`) and zones, over the same 15-minute interval grid as 01.

---

## Aggregator workflow

The **Dash capability page** mirrors this sequence. Each step maps to gold tables — no in-app synthetic data.

| # | Aggregator intent | Data / UI outcome |
|---|---|---|
| 1 | How much **flexibility** is available now? | `short_term_silver_dsr_availability`: `available_up_mw`, `available_down_mw` aggregated by interval |
| 2 | What **prequalified bids** can I place, and where? | `short_term_gold_dsr_bid_stack`: `market`, `qualified_mw`, `bid_price_eur_mwh`, `prequalification_status` |
| 3 | What did we **dispatch**, and did it deliver? | `short_term_gold_dsr_dispatch`: `dispatched_mw`, `delivered_mw`, `delivery_ratio`, `verification_status` |
| 4 | What's the **value**, and per **owner**? | `short_term_gold_dsr_settlement`: `market_revenue_eur`, `owner_payment_eur` (Delta Sharing per owner) |
| 5 | Which **owners / asset types** contribute most? | `short_term_dim_dsr_owners` × settlement; contribution by type |
| 6 | **Negative-price absorb** vs **scarcity dispatch**? | Availability `direction` + dispatch `signal_trigger` (`NEGATIVE_PRICE`, `SCARCITY`, `FREQUENCY`) |
| 7 | **Replay** a prior day? | Trade-date selector on distinct `delivery_date` |

---

## Datasets

### `short_term_dim_dsr_assets`

VPP asset registry — one row per distributed flexible asset.

| Column | Type | Description |
|---|---|---|
| `dsr_asset_id` | STRING | Primary key (e.g. `EVDEPOT_DE_0142`) |
| `owner_id` | STRING | FK → `short_term_dim_dsr_owners` |
| `asset_type` | STRING | `INDUSTRIAL_LOAD`, `EV_DEPOT`, `HEAT_PUMP`, `BTM_BATTERY` |
| `zone_code` | STRING | FK → `short_term_dim_zones` |
| `max_flex_up_mw` | DOUBLE | Max curtailable / dischargeable power |
| `max_flex_down_mw` | DOUBLE | Max absorbable / increasable load |
| `response_time_s` | INT | Activation response time (seconds) |
| `min_runtime_min` | INT | Minimum sustain duration |
| `prequalified_markets` | STRING | CSV of `AFRR`, `MFRR`, `INTRADAY` the asset qualifies for |

### `short_term_dim_dsr_owners`

Third-party asset owners (Delta Sharing recipients).

| Column | Type | Description |
|---|---|---|
| `owner_id` | STRING | Primary key |
| `owner_name` | STRING | Illustrative organisation name |
| `owner_segment` | STRING | `INDUSTRIAL`, `MOBILITY`, `RESIDENTIAL_AGG`, `COMMERCIAL` |
| `share_pct` | DOUBLE | Revenue share to owner (e.g. 0.80) |
| `settlement_currency` | STRING | `EUR` |

### `short_term_bronze_submeter_telemetry`

High-cardinality submeter feed — grain `telemetry_ts` × `dsr_asset_id`.

| Column | Type | Description |
|---|---|---|
| `ingestion_ts` | TIMESTAMP | Landing time |
| `telemetry_ts` | TIMESTAMP | Measurement time |
| `dsr_asset_id` | STRING | FK → registry |
| `consumption_mw` | DOUBLE | Live load (positive = consuming) |
| `baseline_mw` | DOUBLE | Expected load absent any signal |
| `soc_pct` | DOUBLE | BTM battery SoC (null otherwise) |
| `status` | STRING | `ONLINE`, `OFFLINE`, `DISPATCHED` |

### `short_term_silver_dsr_availability`

Per-asset (and aggregable) flexibility per interval — grain `delivery_date` × `dsr_asset_id` × `interval_start`.

| Column | Type | Description |
|---|---|---|
| `delivery_date` | DATE | Trading day |
| `interval_start` | TIMESTAMP | Interval |
| `dsr_asset_id` | STRING | FK → registry |
| `owner_id` | STRING | Denormalised owner |
| `asset_type` | STRING | Denormalised type |
| `zone_code` | STRING | Denormalised zone |
| `baseline_mw` | DOUBLE | Counterfactual baseline (Mosaic AI) |
| `available_up_mw` | DOUBLE | Flex up (reduce load / discharge) |
| `available_down_mw` | DOUBLE | Flex down (increase load / charge) |
| `direction` | STRING | `UP`, `DOWN`, `BOTH`, `NONE` |
| `confidence` | DOUBLE | 0–1 forecast confidence |

### `short_term_gold_dsr_bid_stack`

Aggregated prequalified bid stack per market per interval — grain `delivery_date` × `market` × `zone_code` × `interval_start`.

| Column | Type | Description |
|---|---|---|
| `delivery_date` | DATE | Trading day |
| `interval_start` | TIMESTAMP | Interval |
| `market` | STRING | `AFRR`, `MFRR`, `INTRADAY` |
| `zone_code` | STRING | FK → zones |
| `qualified_mw` | DOUBLE | Aggregate prequalified volume |
| `n_assets` | LONG | Assets in the stack |
| `bid_price_eur_mwh` | DOUBLE | Stack offer price |
| `prequalification_status` | STRING | `QUALIFIED`, `PARTIAL`, `BELOW_MIN_SIZE` |
| `min_size_mw` | DOUBLE | Market minimum bid size |

### `short_term_gold_dsr_dispatch`

Dispatched volume + verified delivery — grain `delivery_date` × `market` × `zone_code` × `interval_start`. **Feeds the control-tower balance ribbon.**

| Column | Type | Description |
|---|---|---|
| `delivery_date` | DATE | Trading day |
| `interval_start` | TIMESTAMP | Interval |
| `market` | STRING | `AFRR`, `MFRR`, `INTRADAY` |
| `zone_code` | STRING | FK → zones |
| `signal_trigger` | STRING | `NEGATIVE_PRICE`, `SCARCITY`, `FREQUENCY` |
| `dispatched_mw` | DOUBLE | Instructed volume (signed: + discharge/curtail, − absorb) |
| `delivered_mw` | DOUBLE | Verified delivered volume |
| `delivery_ratio` | DOUBLE | `delivered / dispatched` |
| `clearing_price_eur_mwh` | DOUBLE | Market clearing price |
| `verification_status` | STRING | `VERIFIED`, `UNDER_DELIVERED`, `PENDING` |

### `short_term_gold_dsr_settlement`

Per-owner settlement — grain `delivery_date` × `owner_id` (Delta Sharing target).

| Column | Type | Description |
|---|---|---|
| `delivery_date` | DATE | Trading day |
| `owner_id` | STRING | FK → owners |
| `owner_name` | STRING | Denormalised |
| `total_delivered_mwh` | DOUBLE | Verified energy delivered |
| `market_revenue_eur` | DOUBLE | Gross market value captured |
| `owner_payment_eur` | DOUBLE | Owner share (`market_revenue × share_pct`) |
| `aggregator_fee_eur` | DOUBLE | Desk retained fee |
| `n_assets_dispatched` | LONG | Owner assets activated |
| `settlement_status` | STRING | `SETTLED`, `PENDING` |

### `short_term_gold_dsr_summary`

One row per `delivery_date` × `snapshot_ts` — headline KPIs for the page banner and outcome cards.

| Column | Type | Description |
|---|---|---|
| `delivery_date` | DATE | Trading day |
| `snapshot_ts` | TIMESTAMP | "As last updated" |
| `headline` | STRING | Primary desk message |
| `total_available_up_mw` | DOUBLE | Peak flex-up available |
| `total_available_down_mw` | DOUBLE | Peak flex-down available |
| `total_dispatched_mwh` | DOUBLE | Energy dispatched in window |
| `total_market_revenue_eur` | DOUBLE | Gross value captured |
| `total_owner_payments_eur` | DOUBLE | Paid to owners |
| `avg_delivery_ratio` | DOUBLE | Mean verified delivery |
| `n_assets_online` | LONG | Assets online in the fleet |
| `n_owners` | LONG | Distinct owners settled |

---

## App UI (Dash) — DSR & market access desk

Implements the [aggregator workflow](#aggregator-workflow). Inherits [`instructions.md`](./instructions.md) (header warehouse, no in-app mock data, loading states, full-width layout, no auto-poll).

| Item | Value |
|---|---|
| **Route** | `/short-term/dsr` |
| **Sidebar label** | DSR & Market Access |
| **Page module (convention)** | `app/pages/short_term_dsr.py` |
| **Data access** | `app/uc_pages.py` + `app/uc_sql.py`; header `sql-warehouse-dropdown` |

### Page layout

Full-width **hero**, then **toolbar**, then analytics.

| Block | Content |
|---|---|
| **Hero** | Eyebrow, **VPP / Market Access** + **Delta Sharing** badges, title, aggregator-facing summary, **Presenter guide** button |
| **Toolbar** | Trade date, market (aFRR/mFRR/Intraday), asset-type filter, refresh |
| **Status banner** | Flex available up/down, dispatched MWh, headline |
| **Outcome cards** | Market revenue €, owner payments €, avg delivery ratio, assets online |
| **Availability chart** | Flex up/down by interval; absorb (negative-price) vs dispatch (scarcity) shading |
| **Bid-stack panel** | Prequalified MW by market with status and bid price |
| **Dispatch & verification** | Dispatched vs delivered by interval; delivery ratio; signal trigger |
| **Settlement table** | Per-owner revenue, payment, fee, assets dispatched (Delta Sharing note) |
| **Contribution breakdown** | Revenue / flex by asset type or owner segment |
| **Footnote** | Selected trade date only; illustrative data |
| **Presenter guide** | Problem → cross-desk link → story → toolbar → banner → cards → charts → settlement → who uses |

### Presenter guide (in-app modal)

Business narrative for demos — in the page module:

| Section | Message |
|---|---|
| What problem this solves | Monetise distributed flexibility the desk doesn't own; aggregate, qualify, dispatch, verify, settle |
| How this relates to the control tower | DSR dispatch contributes to the balance ribbon (capability 02) |
| Story to tell | Midday negative price → absorb (charge EVs, pre-cool loads); evening scarcity → dispatch into balancing; per-owner settlement auto-produced and shared |
| Toolbar | Trade date, market, asset type, refresh |
| Status banner | Flex available, dispatched MWh, headline |
| Outcome cards | Market revenue, owner payments, delivery ratio, assets online |
| Charts | Availability, bid stack, dispatch vs delivered |
| Settlement | Per-owner payments via Delta Sharing |
| Who uses this view | Aggregator/VPP desk, market-access ops, asset owners (shared), risk |
| Platform close (optional) | Lakeflow high-cardinality ingest + Mosaic AI baselines + Spark optimization + Delta Sharing |

| Workflow intent | UI block |
|---|---|
| Flexibility available | Availability chart + banner |
| What can I bid | Bid-stack panel |
| What delivered | Dispatch & verification |
| Value per owner | Settlement table |
| Contribution | Breakdown chart |
| Replay prior day | Trade-date selector |

### Empty and error states

| Condition | Message / behaviour |
|---|---|
| No warehouse selected | Prompt to select a running warehouse (no mock data) |
| No DSR data | Prompt to run `energy_trading_demo_data` (notebooks **01 → 03**) |
| Query failure | Show error text; do not fabricate charts |

### Widget-to-dataset binding

| UI block | Primary datasets | Key fields |
|---|---|---|
| Status banner | `short_term_gold_dsr_summary` | `headline`, `total_available_up_mw`, `total_available_down_mw`, `total_dispatched_mwh` |
| Outcome cards | `short_term_gold_dsr_summary` | `total_market_revenue_eur`, `total_owner_payments_eur`, `avg_delivery_ratio`, `n_assets_online` |
| Availability chart | `short_term_silver_dsr_availability` | `interval_start`, `available_up_mw`, `available_down_mw`, `direction` |
| Bid-stack panel | `short_term_gold_dsr_bid_stack` | `market`, `qualified_mw`, `bid_price_eur_mwh`, `prequalification_status` |
| Dispatch & verification | `short_term_gold_dsr_dispatch` | `dispatched_mw`, `delivered_mw`, `delivery_ratio`, `signal_trigger`, `verification_status` |
| Settlement table | `short_term_gold_dsr_settlement`, `short_term_dim_dsr_owners` | `owner_name`, `market_revenue_eur`, `owner_payment_eur`, `aggregator_fee_eur` |
| Contribution breakdown | `short_term_gold_dsr_settlement` × `short_term_dim_dsr_assets` | revenue/flex by `asset_type` / `owner_segment` |
| Trade-date list | `short_term_dim_intervals` | `DISTINCT delivery_date` |

---

## Relationships

| Direction | Dependency |
|---|---|
| **Upstream** | **01** — shared dimensions (`short_term_dim_zones`, `short_term_dim_intervals`); intraday price signals inform bid prices |
| **Downstream** | **02 Control tower** — `short_term_gold_dsr_dispatch` contributes to the balance ribbon and dispatch view |
| **Shared** | Owns the DSR registry (`short_term_dim_dsr_assets`, `short_term_dim_dsr_owners`) and Delta Sharing settlement |

Changes to `short_term_gold_dsr_dispatch` grain must coordinate with the control tower (02). Settlement schema changes affect Delta Sharing recipients (owners).

## Out of scope

- Real submeter / VPP platform connectivity (synthetic fleet only)
- True high-cardinality streaming in the demo (batch gold with `snapshot_ts`; streaming documented)
- Real TSO prequalification rules per country (single illustrative min-size / response-time model)
- Production Delta Sharing recipient provisioning (settlement table shape only; sharing documented)
- Contractual / billing logic beyond `share_pct` split
- In-app mock data (see [`instructions.md`](./instructions.md))
