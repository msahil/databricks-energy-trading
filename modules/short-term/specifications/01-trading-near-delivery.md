# 01 — Trading near delivery

> Parent brief: [`main.md`](./main.md) (Capability 1). Platform and app conventions: [`instructions.md`](./instructions.md).

## Summary

As weather updates land through the day, the desk **re-forecasts** 15-minute renewable generation, computes the **residual physical delta** against the long-term hedge, and **squares** it on the continuous Intraday (SIDC/XBID) market **before the cross-border gate closes**. In parallel it watches **imbalance exposure** — the gap between commercial nominations and live metering — and projects the **cash-out cost** of entering an interval short or long.

This capability owns the module's **shared dimensions** (`short_term_dim_zones`, `short_term_dim_assets`, `short_term_dim_intervals`) consumed by capabilities 02 and 03. It also showcases a **backtest & replay** loop: historical 15-minute intervals are replayed via **Delta time-travel** and strategy variants scored in **MLflow** before a squaring rule is armed live. Data is **illustrative** but follows prompt-desk conventions.

## Databricks fit

| Capability | Role |
|---|---|
| **Structured Streaming (Real-Time Mode)** | Sub-second ingest of weather + SCADA telemetry; demo materialises the same gold in batch |
| **Lakeflow Declarative Pipelines (DLT)** | Continuous cleanse → forecast → square pipeline |
| **Multi-Stream Temporal Joins** | Nominations × live metering for imbalance exposure |
| **Delta time travel + MLflow** | Replay historical intervals; track backtested squaring strategies |
| **Unity Catalog** | Governed Delta tables; semantics in [`../notebooks/uc_table_comments.py`](../notebooks/uc_table_comments.py) |

## Notebook and tables

[`../notebooks/01_trading_near_delivery.ipynb`](../notebooks/01_trading_near_delivery.ipynb) materialises:

| Layer | Tables |
|---|---|
| Dimensions (shared) | `short_term_dim_zones`, `short_term_dim_assets`, `short_term_dim_intervals` |
| Bronze | `short_term_bronze_weather_obs`, `short_term_bronze_scada_telemetry` |
| Silver | `short_term_silver_generation_forecast`, `short_term_silver_nominations` |
| Gold — squaring | `short_term_gold_squaring_actions`, `short_term_gold_near_delivery_summary` |
| Gold — imbalance | `short_term_gold_imbalance_exposure` |
| Gold — backtest | `short_term_gold_backtest_runs` |

**Catalog.schema:** `energy_utilities.energy_trading2` (override with `DEMO_UC_CATALOG` / `DEMO_UC_SCHEMA`). Seed job: `energy_trading_demo_data` (run notebook **01 first** — it owns the shared dimensions).

**Trading-day grid (illustrative):** one or more `delivery_date`s of **96 × 15-minute intervals**; five zones (`DE`, `NL`, `FR`, `BE`, `AT`); the 1,000 MW portfolio assets from `main.md`. The latest `forecast_ts` per interval is the live re-forecast; earlier ones support replay.

---

## Trader near-delivery workflow

The **Dash capability page** mirrors this sequence. Each step maps to gold tables — no in-app synthetic data.

| # | Trader intent | Data / UI outcome |
|---|---|---|
| 1 | Where am I **long / short** right now? | Net delta per interval from `short_term_gold_squaring_actions.net_delta_mw`; headline from `short_term_gold_near_delivery_summary` |
| 2 | Which assets are **deviating** from forecast? | Forecast vs latest from `short_term_silver_generation_forecast` (`forecast_deviation_mw`, `deviation_severity`) |
| 3 | How long until the **gate closes**? | `gate_close_ts`, `minutes_to_gate` per zone on squaring actions |
| 4 | What's the **squaring action**? | `recommended_side`, `recommended_mw`, `expected_price_eur_mwh` per interval |
| 5 | What's my **cash-out risk** if I do nothing? | `short_term_gold_imbalance_exposure`: `net_imbalance_mw`, `system_balance_direction`, `projected_cashout_eur` |
| 6 | Is the **grid short or long**? | `system_balance_direction` (`LONG`/`SHORT`) and `imbalance_price_eur_mwh` |
| 7 | Would this rule have **paid off**? | `short_term_gold_backtest_runs`: realized P&L, hit-rate, cash-out avoided per strategy variant |
| 8 | **Replay** a prior trading day / interval window? | Trade-date selector on distinct `delivery_date`; replay via earlier `forecast_ts` (Delta time-travel in production) |

**Gate rule (illustrative):** an interval is `OPEN` for squaring until `gate_close_ts` (15–30 min before delivery), then `CLOSED`; closed intervals fall through to imbalance/cash-out.

---

## Datasets

### `short_term_dim_zones`

Shared dimension — one row per bidding zone (owned here, used by 02 & 03).

| Column | Type | Description |
|---|---|---|
| `zone_code` | STRING | Primary key: `DE`, `NL`, `FR`, `BE`, `AT` |
| `country` | STRING | Country name |
| `tso_name` | STRING | Transmission System Operator (e.g. `50Hertz/Amprion/TenneT/TransnetBW`) |
| `imbalance_area` | STRING | TSO imbalance/control area label |
| `eic_code` | STRING | Illustrative EIC identifier |
| `currency` | STRING | `EUR` |

### `short_term_dim_assets`

Shared dimension — the physical portfolio from `main.md` (used by 02; DSR registry lives in 03).

| Column | Type | Description |
|---|---|---|
| `asset_id` | STRING | Primary key (e.g. `CCGT_DE_001`, `WIND_DE_001`, `SOLAR_DE_001`, `BATT_DE_001`) |
| `asset_type` | STRING | `CCGT`, `WIND_ONSHORE`, `SOLAR_PV`, `BATTERY` |
| `nameplate_mw` | DOUBLE | Rated power |
| `zone_code` | STRING | FK → `short_term_dim_zones` |
| `efficiency` | DOUBLE | CCGT only (e.g. 0.55); null otherwise |
| `emission_factor_tco2_mwh` | DOUBLE | CCGT only (e.g. 0.364); null otherwise |
| `energy_capacity_mwh` | DOUBLE | Battery only (e.g. 200); null otherwise |
| `is_dispatchable` | BOOLEAN | True for CCGT / battery / hydro; false for wind / solar |
| `annotation` | STRING | E.g. "fast start-stop", "2h duration battery" |

### `short_term_dim_intervals`

Shared time spine — one row per 15-minute delivery interval (used by 02 & 03).

| Column | Type | Description |
|---|---|---|
| `delivery_date` | DATE | Trading / delivery day |
| `interval_start` | TIMESTAMP | Interval start (15-min grain) |
| `interval_end` | TIMESTAMP | Interval end |
| `interval_index` | INT | 1–96 within the day |
| `hour` | INT | 0–23 |
| `is_peak` | BOOLEAN | Peak-load window flag |
| `solar_window` | BOOLEAN | Midday solar-peak flag (negative-price risk) |

### Bronze — raw landing

#### `short_term_bronze_weather_obs`

Streamed weather observations / re-forecast inputs — grain `forecast_ts` × `zone_code` × `interval_start`.

| Column | Type | Description |
|---|---|---|
| `ingestion_ts` | TIMESTAMP | Landing time |
| `forecast_ts` | TIMESTAMP | Re-forecast issue time |
| `source` | STRING | `ECMWF`, `GFS`, `VENDOR_X`, `SATELLITE` |
| `zone_code` | STRING | FK → zones |
| `interval_start` | TIMESTAMP | Target interval |
| `wind_speed_ms` | DOUBLE | Forecast wind speed |
| `solar_irradiance_wm2` | DOUBLE | Forecast irradiance |
| `temperature_c` | DOUBLE | Forecast temperature |
| `cloud_cover_pct` | DOUBLE | 0–100 |

#### `short_term_bronze_scada_telemetry`

Live asset telemetry — grain `telemetry_ts` × `asset_id`.

| Column | Type | Description |
|---|---|---|
| `ingestion_ts` | TIMESTAMP | Landing time |
| `telemetry_ts` | TIMESTAMP | Measurement time |
| `asset_id` | STRING | FK → assets |
| `actual_output_mw` | DOUBLE | Metered output |
| `availability_pct` | DOUBLE | 0–100 |
| `status` | STRING | `RUNNING`, `CURTAILED`, `OUTAGE` |

### Silver — conformed

#### `short_term_silver_generation_forecast`

Re-forecast vs actual per asset per interval — grain `forecast_ts` × `asset_id` × `interval_start`.

| Column | Type | Description |
|---|---|---|
| `delivery_date` | DATE | Trading day |
| `interval_start` | TIMESTAMP | Target interval |
| `forecast_ts` | TIMESTAMP | Re-forecast issue time (latest = live) |
| `asset_id` | STRING | FK → assets |
| `zone_code` | STRING | Denormalised zone |
| `forecast_mw` | DOUBLE | Current forecast output |
| `prev_forecast_mw` | DOUBLE | Prior re-forecast |
| `actual_mw` | DOUBLE | Metered (null for future intervals) |
| `forecast_deviation_mw` | DOUBLE | `forecast_mw − prev_forecast_mw` |
| `deviation_severity` | STRING | `OK`, `WATCH`, `SEVERE` |

#### `short_term_silver_nominations`

Commercial nominations (schedule) per zone per interval — grain `delivery_date` × `zone_code` × `interval_start`.

| Column | Type | Description |
|---|---|---|
| `delivery_date` | DATE | Trading day |
| `interval_start` | TIMESTAMP | Interval |
| `zone_code` | STRING | FK → zones |
| `nominated_mw` | DOUBLE | Scheduled net position (signed) |
| `hedge_mw` | DOUBLE | Long-term hedge handed over (from curve desk) |
| `source` | STRING | `SCHEDULE`, `HEDGE_HANDOVER` |

### Gold — squaring

#### `short_term_gold_squaring_actions`

**Primary squaring table** — grain `delivery_date` × `zone_code` × `interval_start` (latest `forecast_ts`).

| Column | Type | Description |
|---|---|---|
| `delivery_date` | DATE | Trading day |
| `interval_start` | TIMESTAMP | Interval |
| `interval_index` | INT | 1–96 |
| `zone_code` | STRING | FK → zones |
| `forecast_ts` | TIMESTAMP | Re-forecast feeding this action |
| `forecast_gen_mw` | DOUBLE | Total renewable forecast for zone |
| `nominated_mw` | DOUBLE | Net commercial nomination |
| `net_delta_mw` | DOUBLE | Long(+)/short(−) residual to square |
| `recommended_side` | STRING | `BUY`, `SELL`, `FLAT` |
| `recommended_mw` | DOUBLE | Suggested squaring volume |
| `expected_price_eur_mwh` | DOUBLE | Indicative intraday clearing price |
| `gate_close_ts` | TIMESTAMP | XBID/SIDC gate close for this interval |
| `minutes_to_gate` | INT | Countdown at `forecast_ts` |
| `gate_status` | STRING | `OPEN`, `CLOSING`, `CLOSED` |

#### `short_term_gold_near_delivery_summary`

One row per `delivery_date` × `snapshot_ts` — headline KPIs for the page banner and outcome cards.

| Column | Type | Description |
|---|---|---|
| `delivery_date` | DATE | Trading day |
| `snapshot_ts` | TIMESTAMP | "As last updated" |
| `headline` | STRING | Primary desk action message |
| `net_open_position_mw` | DOUBLE | Sum of unsquared delta across open intervals |
| `n_intervals_open` | LONG | Intervals still tradable |
| `n_intervals_closing` | LONG | Intervals inside gate-closing window |
| `n_severe_deviations` | LONG | Assets in `SEVERE` deviation |
| `projected_cashout_eur` | DOUBLE | Total projected cash-out if unsquared |
| `system_balance_direction` | STRING | Net grid `LONG` / `SHORT` |
| `next_gate_close_ts` | TIMESTAMP | Soonest gate close across zones |

### Gold — imbalance

#### `short_term_gold_imbalance_exposure`

Imbalance and cash-out projection — grain `delivery_date` × `zone_code` × `interval_start`.

| Column | Type | Description |
|---|---|---|
| `delivery_date` | DATE | Trading day |
| `interval_start` | TIMESTAMP | Interval |
| `zone_code` | STRING | FK → zones |
| `nominated_mw` | DOUBLE | What was promised |
| `metered_mw` | DOUBLE | What assets actually produced (null for future) |
| `net_imbalance_mw` | DOUBLE | `metered − nominated` (signed) |
| `system_balance_direction` | STRING | TSO grid `LONG` / `SHORT` |
| `imbalance_price_eur_mwh` | DOUBLE | Illustrative single/dual cash-out price |
| `projected_cashout_eur` | DOUBLE | `net_imbalance_mw × imbalance_price` (signed cost) |
| `exposure_severity` | STRING | `OK`, `WATCH`, `BREACH` |

### Gold — backtest

#### `short_term_gold_backtest_runs`

Backtested squaring strategy variants over historical intervals (MLflow-tracked) — grain `run_id` × `strategy`.

| Column | Type | Description |
|---|---|---|
| `run_id` | STRING | MLflow run id (or synthetic surrogate) |
| `strategy` | STRING | `EARLY_SQUARE`, `WAIT_FOR_GATE`, `THRESHOLD_DEVIATION`, `BASELINE_NO_TRADE` |
| `backtest_start_date` | DATE | First replayed delivery day |
| `backtest_end_date` | DATE | Last replayed delivery day |
| `n_intervals` | LONG | Intervals replayed |
| `realized_pnl_eur` | DOUBLE | Strategy P&L over the window |
| `cashout_avoided_eur` | DOUBLE | Cash-out saved vs `BASELINE_NO_TRADE` |
| `hit_rate_pct` | DOUBLE | % intervals where the rule improved P&L |
| `avg_minutes_before_gate` | DOUBLE | Mean lead time of squaring trades |
| `is_recommended` | BOOLEAN | Best variant flag for the page |

---

## App UI (Dash) — near-delivery desk

Implements the [near-delivery workflow](#trader-near-delivery-workflow). Inherits global app rules from [`instructions.md`](./instructions.md) (header warehouse, no in-app mock series, loading states, full-width layout, no auto-poll).

| Item | Value |
|---|---|
| **Route** | `/short-term/near-delivery` |
| **Sidebar label** | Trading near delivery |
| **Page module (convention)** | `app/pages/short_term_near_delivery.py` |
| **Data access** | `app/uc_pages.py` + `app/uc_sql.py`; header `sql-warehouse-dropdown`; gold/silver datasets in this spec |

### Page layout

Full-width **hero**, then **toolbar**, then analytics (loaded via header warehouse).

| Block | Content |
|---|---|
| **Hero** | Eyebrow, **Streaming** badge, title, trader-facing summary, **Presenter guide** button |
| **Streaming callout** | Business-focused note: sub-second re-forecast → square before gate (no infra jargon) |
| **Toolbar** | Trade date, zone, interval-window filter, refresh (no auto-poll) |
| **Status banner** | Net open position, soonest gate close, system balance direction, headline |
| **Outcome cards** | Net open MW, intervals open/closing, severe deviations, projected cash-out € |
| **Squaring chart** | Net delta by interval with gate-close markers; recommended side colouring |
| **Deviation grid** | Assets with forecast vs prev, deviation MW, severity |
| **Imbalance & cash-out** | Net imbalance by interval + projected cash-out; system-balance strip |
| **Backtest panel** | Strategy variants with P&L, cash-out avoided, hit-rate; recommended flag; "replay yesterday" |
| **Footnote** | Selected trade date only; illustrative data |
| **Presenter guide** | Same section order as long-term pages (problem → cross-desk link → story → toolbar → banner → cards → charts → backtest → who uses) |

### Presenter guide (in-app modal)

Business narrative for demos — not setup or architecture. Key sections in the page module:

| Section | Message |
|---|---|
| What problem this solves | Enter every delivery interval balanced; square the residual before the gate; avoid cash-out |
| How this relates to the curve desk | Inherits the P50 hedge; squares the residual volume/profile risk the curve left open |
| How this relates to the control tower | Squaring + imbalance feed the control-tower balance ribbon (capability 02) |
| Story to tell | Long/short now → deviating assets → gate countdown → squaring action → cash-out risk → backtest proof |
| Toolbar | Trade date, zone, interval window, refresh |
| Status banner | Net open position, next gate, grid direction |
| Outcome cards | Open MW, intervals open/closing, severe deviations, cash-out |
| Charts | Squaring by interval, deviation grid, imbalance & cash-out |
| Backtest | Replay yesterday; prove a rule before arming live (Delta time-travel + MLflow) |
| Who uses this view | Intraday traders, schedulers, risk |

### Empty and error states

| Condition | Message / behaviour |
|---|---|
| No warehouse selected in header | Prompt to select a running warehouse (no mock data) |
| Warehouse selected, no data | Prompt to run `energy_trading_demo_data`, then retry |
| Query failure | Show error text; do not fabricate charts |

### Widget-to-dataset binding

| UI block | Primary datasets | Key fields |
|---|---|---|
| Status banner | `short_term_gold_near_delivery_summary` | `headline`, `net_open_position_mw`, `next_gate_close_ts`, `system_balance_direction` |
| Outcome cards | `short_term_gold_near_delivery_summary` | `n_intervals_open`, `n_intervals_closing`, `n_severe_deviations`, `projected_cashout_eur` |
| Squaring chart | `short_term_gold_squaring_actions` | `interval_start`, `net_delta_mw`, `recommended_side`, `gate_close_ts`, `gate_status` |
| Deviation grid | `short_term_silver_generation_forecast` | `asset_id`, `forecast_mw`, `prev_forecast_mw`, `forecast_deviation_mw`, `deviation_severity` |
| Imbalance & cash-out | `short_term_gold_imbalance_exposure` | `net_imbalance_mw`, `imbalance_price_eur_mwh`, `projected_cashout_eur`, `system_balance_direction` |
| Backtest panel | `short_term_gold_backtest_runs` | `strategy`, `realized_pnl_eur`, `cashout_avoided_eur`, `hit_rate_pct`, `is_recommended` |
| Trade-date list | `short_term_dim_intervals` | `DISTINCT delivery_date` |

---

## Relationships

| Direction | Dependency |
|---|---|
| **Upstream** | Long-term **Forward curve / VaR** define the hedge handover (`hedge_mw` in `short_term_silver_nominations`); ingests bronze from synthetic/API-shaped weather + SCADA |
| **Downstream** | **02 Control tower** — consumes `short_term_gold_squaring_actions` and `short_term_gold_imbalance_exposure` for the balance ribbon; **03 DSR** — uses shared dimensions and squaring price signals |
| **Shared** | Owns `short_term_dim_zones`, `short_term_dim_assets`, `short_term_dim_intervals` — used by 02 and 03 |

Schema or grain changes to the shared dimensions or to `short_term_gold_squaring_actions` require coordination with 02 and 03 owners.

## Out of scope

- Live EPEX / Nord Pool / XBID connectivity (synthetic intervals only)
- True sub-second streaming in the demo (batch materialisation of the same gold; streaming documented)
- Order-level execution / FIX gateway integration
- Real TSO imbalance settlement rules per country (single illustrative cash-out price)
- In-app mock or generated series (see [`instructions.md`](./instructions.md))
