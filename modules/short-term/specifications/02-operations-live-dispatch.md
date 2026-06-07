# 02 — 24/7 Operations & Live Dispatch (Control Tower)

> Parent brief: [`main.md`](./main.md) (Capability 2). Platform and app conventions: [`instructions.md`](./instructions.md).

## Summary

The **control tower** is the module centerpiece: a single live operations view that runs the physical portfolio around the clock. It **aggregates** the squaring and imbalance outputs from [`01-trading-near-delivery.md`](./01-trading-near-delivery.md) and the flexibility/dispatch from [`03-dsr-market-access.md`](./03-dsr-market-access.md), adds **per-asset dispatch recommendations**, **grid frequency / aFRR** signals, **market gate** countdowns, a streamed **REMIT event feed**, and an **agentic trading copilot** that drafts the next action with rationale. An on-shift operator sees the whole book, acts on the highest-value decision, and hands over cleanly.

Mosaic AI serves the **dispatch policy** (Charge / Hold / Discharge, Ramp, Bid into aFRR). The **copilot** is an Agent Bricks / multi-agent supervisor over Genie + Vector Search. Data is **illustrative** but follows real ops-desk mechanics.

## Databricks fit

| Capability | Role |
|---|---|
| **Structured Streaming (Real-Time Mode)** | Live telemetry, frequency, gates, events; demo materialises gold in batch with `snapshot_ts` |
| **Mosaic AI Model Serving** | Dispatch policy → per-asset recommended action + expected margin |
| **Lakehouse Monitoring** | Threshold breaches, drift, alerting feeding the alerts zone |
| **Agent Bricks (multi-agent) + Vector Search + Genie** | Trading copilot: classify event → retrieve precedent → query live tables → draft action |
| **Databricks Apps** | The live control-tower dashboard itself |
| **Unity Catalog** | Governed Delta tables; semantics in [`../notebooks/uc_table_comments.py`](../notebooks/uc_table_comments.py) |

## Notebook and tables

[`../notebooks/02_operations_live_dispatch.ipynb`](../notebooks/02_operations_live_dispatch.ipynb) materialises:

| Layer | Tables |
|---|---|
| Inputs (capability 01) | `short_term_dim_zones`, `short_term_dim_assets`, `short_term_dim_intervals`, `short_term_gold_squaring_actions`, `short_term_gold_imbalance_exposure` |
| Inputs (capability 03) | `short_term_gold_dsr_dispatch` (DSR contribution to dispatch & balance) |
| Bronze/Silver | `short_term_silver_grid_frequency`, `short_term_silver_market_gates` |
| Gold — balance & dispatch | `short_term_gold_portfolio_balance`, `short_term_gold_asset_dispatch` |
| Gold — events & copilot | `short_term_gold_remit_events`, `short_term_gold_copilot_recommendations` |
| Gold — summary | `short_term_gold_control_tower_summary` |

**Catalog.schema:** `energy_utilities.energy_trading2` (override with `DEMO_UC_CATALOG` / `DEMO_UC_SCHEMA`). Seed job: `energy_trading_demo_data` (run notebook **01 before 02**; **03** before 02 if the DSR dispatch contribution is shown).

**Aggregator role:** the control tower does not re-derive squaring or imbalance — it **reads** `short_term_gold_squaring_actions` and `short_term_gold_imbalance_exposure` (01) and `short_term_gold_dsr_dispatch` (03), and adds dispatch, frequency, gates, events, and copilot on top. Keep the shared interval/zone/asset grain aligned.

---

## Operator control-tower workflow

The **Dash control-tower page** is organised as the six zones from `main.md` plus the copilot. Each zone maps to gold tables — no in-app synthetic data. The trade-date / interval selector is the "now" cursor; refresh re-queries (simulating the live stream).

| Zone | Operator question | Data / UI outcome |
|---|---|---|
| **Portfolio balance ribbon** | *Am I balanced into the next intervals?* | `short_term_gold_portfolio_balance`: `net_position_mw`, `system_balance_direction`, `projected_cashout_eur` |
| **Asset dispatch panel** | *What should each asset do now?* | `short_term_gold_asset_dispatch`: per-asset `recommended_action`, `soc_pct`, `clean_spark_spread_eur`, `expected_margin_eur` |
| **Grid & frequency panel** | *Is the grid short/long, am I called?* | `short_term_silver_grid_frequency`: `frequency_hz`, `afrr_signal_mw`, `reserve_obligation_mw` |
| **Market gate panel** | *How long until I must act?* | `short_term_silver_market_gates`: `market`, `gate_close_ts`, `minutes_to_gate`, `order_book_depth_mw` |
| **Event & REMIT feed** | *What just changed, how big?* | `short_term_gold_remit_events`: `event_type`, `affected_zone`, `capacity_mw`, `impact_eur_mwh`, `severity` |
| **Trading copilot** | *What's the play, and why?* | `short_term_gold_copilot_recommendations`: `recommendation`, `rationale`, `linked_event_id`, `confidence` |
| **Alerts & shift handover** | *What must the next shift not drop?* | `short_term_gold_control_tower_summary`: `pnl_since_shift_eur`, `n_open_alerts`, `handover_notes` |

---

## Datasets

### `short_term_silver_grid_frequency`

Live grid frequency and balancing signals — grain `snapshot_ts` × `zone_code`.

| Column | Type | Description |
|---|---|---|
| `snapshot_ts` | TIMESTAMP | Measurement time |
| `delivery_date` | DATE | Trading day |
| `interval_start` | TIMESTAMP | Interval |
| `zone_code` | STRING | FK → `short_term_dim_zones` |
| `frequency_hz` | DOUBLE | Grid frequency (≈50.0) |
| `frequency_deviation_mhz` | DOUBLE | Deviation from 50 Hz in mHz |
| `afrr_signal_mw` | DOUBLE | aFRR activation signal (signed) |
| `mfrr_signal_mw` | DOUBLE | mFRR activation signal (signed) |
| `reserve_obligation_mw` | DOUBLE | Our prequalified reserve commitment |
| `signal_state` | STRING | `NEUTRAL`, `CALL_UP`, `CALL_DOWN` |

### `short_term_silver_market_gates`

Gate countdowns and liquidity per market per zone — grain `snapshot_ts` × `market` × `zone_code`.

| Column | Type | Description |
|---|---|---|
| `snapshot_ts` | TIMESTAMP | "As last updated" |
| `delivery_date` | DATE | Trading day |
| `market` | STRING | `DAY_AHEAD`, `INTRADAY_AUCTION`, `XBID_CONTINUOUS`, `AFRR` |
| `zone_code` | STRING | FK → zones |
| `next_gate_close_ts` | TIMESTAMP | Next gate close |
| `minutes_to_gate` | INT | Countdown |
| `order_book_depth_mw` | DOUBLE | Liquidity at touch |
| `best_bid_eur_mwh` | DOUBLE | Top of book bid |
| `best_ask_eur_mwh` | DOUBLE | Top of book ask |
| `gate_status` | STRING | `OPEN`, `CLOSING`, `CLOSED` |

### `short_term_gold_portfolio_balance`

Balance ribbon — grain `delivery_date` × `interval_start` × `snapshot_ts` (aggregated across zones + DSR).

| Column | Type | Description |
|---|---|---|
| `delivery_date` | DATE | Trading day |
| `interval_start` | TIMESTAMP | Interval |
| `snapshot_ts` | TIMESTAMP | "As last updated" |
| `net_position_mw` | DOUBLE | Portfolio net long(+)/short(−), incl. squaring + DSR |
| `squaring_delta_mw` | DOUBLE | Contribution from 01 squaring actions |
| `dsr_contribution_mw` | DOUBLE | Contribution from 03 DSR dispatch |
| `system_balance_direction` | STRING | TSO grid `LONG` / `SHORT` |
| `projected_cashout_eur` | DOUBLE | If left unbalanced into delivery |
| `balance_state` | STRING | `BALANCED`, `WATCH`, `EXPOSED` |

### `short_term_gold_asset_dispatch`

Per-asset live state + Mosaic AI recommended action — grain `delivery_date` × `interval_start` × `asset_id` × `snapshot_ts`.

| Column | Type | Description |
|---|---|---|
| `delivery_date` | DATE | Trading day |
| `interval_start` | TIMESTAMP | Interval |
| `snapshot_ts` | TIMESTAMP | "As last updated" |
| `asset_id` | STRING | FK → `short_term_dim_assets` |
| `asset_type` | STRING | Denormalised |
| `current_output_mw` | DOUBLE | Live metered output |
| `soc_pct` | DOUBLE | Battery state of charge (null for non-battery) |
| `cycle_budget_remaining` | DOUBLE | Battery daily cycles left (null otherwise) |
| `clean_spark_spread_eur` | DOUBLE | CCGT CSS (null otherwise) |
| `recommended_action` | STRING | `CHARGE`, `HOLD`, `DISCHARGE`, `RAMP_UP`, `RAMP_DOWN`, `BID_AFRR`, `IDLE` |
| `expected_margin_eur` | DOUBLE | Expected € from the action this interval |
| `policy_confidence` | DOUBLE | 0–1 from the serving model |
| `constraint_flag` | STRING | `OK`, `SOC_LIMIT`, `RAMP_LIMIT`, `MIN_RUNTIME` |

### `short_term_gold_remit_events`

Streamed REMIT / outage / weather-shock events with impact scoring — grain `event_id`.

| Column | Type | Description |
|---|---|---|
| `event_id` | STRING | Primary key |
| `event_ts` | TIMESTAMP | Broadcast time |
| `delivery_date` | DATE | Trading day affected |
| `event_type` | STRING | `THERMAL_TRIP`, `INTERCONNECTOR_OUTAGE`, `WIND_RAMP_DOWN`, `SOLAR_SHOCK`, `NUCLEAR_TRIP` |
| `affected_zone` | STRING | FK → zones |
| `asset_or_unit` | STRING | Affected unit label (illustrative) |
| `capacity_mw` | DOUBLE | Capacity removed/added |
| `impact_eur_mwh` | DOUBLE | Estimated price impact |
| `impact_horizon_hours` | INT | Expected duration of impact |
| `severity` | STRING | `INFO`, `WATCH`, `CRITICAL` |
| `raw_message` | STRING | Unstructured REMIT text (Vector Search source) |

### `short_term_gold_copilot_recommendations`

Agent-drafted recommendations linked to events — grain `recommendation_id`.

| Column | Type | Description |
|---|---|---|
| `recommendation_id` | STRING | Primary key |
| `generated_ts` | TIMESTAMP | When the agent produced it |
| `delivery_date` | DATE | Trading day |
| `linked_event_id` | STRING | FK → `short_term_gold_remit_events` (nullable) |
| `recommendation` | STRING | Action text (e.g. "Discharge BATT_DE_001 80 MW; buy 60 MW DE intraday") |
| `rationale` | STRING | Grounded reasoning with cited figures |
| `expected_pnl_impact_eur` | DOUBLE | Estimated € benefit |
| `confidence` | DOUBLE | 0–1 supervisor confidence |
| `agent_trace` | STRING | Which sub-agents contributed (classify / retrieve / query) |
| `status` | STRING | `PROPOSED`, `ACCEPTED`, `REJECTED` (demo default `PROPOSED`) |

### `short_term_gold_control_tower_summary`

One row per `delivery_date` × `snapshot_ts` — header banner, P&L, alerts, shift handover.

| Column | Type | Description |
|---|---|---|
| `delivery_date` | DATE | Trading day |
| `snapshot_ts` | TIMESTAMP | "As last updated" |
| `headline` | STRING | Primary ops message |
| `pnl_since_shift_eur` | DOUBLE | P&L since shift start |
| `net_position_mw` | DOUBLE | Current portfolio net position |
| `balance_state` | STRING | `BALANCED` / `WATCH` / `EXPOSED` |
| `n_open_alerts` | LONG | Lakehouse-monitoring alerts open |
| `n_critical_events` | LONG | `CRITICAL` events in window |
| `n_assets_actionable` | LONG | Assets with a non-`HOLD`/`IDLE` recommendation |
| `top_copilot_recommendation_id` | STRING | Highest-confidence open recommendation |
| `shift_start_ts` | TIMESTAMP | Current shift start |
| `handover_notes` | STRING | Open actions for the next shift |

---

## App UI (Dash) — control tower

Implements the [control-tower workflow](#operator-control-tower-workflow). Inherits [`instructions.md`](./instructions.md) (header warehouse, no in-app mock data, loading states, full-width layout, no auto-poll). This page is a **live operations dashboard** — multi-zone, not a single-snapshot analytics page.

| Item | Value |
|---|---|
| **Route** | `/short-term/control-tower` |
| **Sidebar label** | 24/7 Operations & Live Dispatch |
| **Page module (convention)** | `app/pages/short_term_control_tower.py` |
| **Data access** | `app/uc_pages.py` + `app/uc_sql.py`; header `sql-warehouse-dropdown` |

### Page layout

Full-width **hero**, then the **"now" toolbar**, then the six zones (+ copilot) as a responsive grid.

| Block | Content |
|---|---|
| **Hero** | Eyebrow, **Operations** + **Mosaic AI** badges, title, ops-facing summary, **Presenter guide** button |
| **"Now" toolbar** | Trade date, interval cursor, zone filter, refresh (simulates live stream; no auto-poll) |
| **Status banner** | Balance state, P&L since shift, open alerts, headline |
| **Balance ribbon** | Net position by interval; system-balance overlay; projected cash-out |
| **Asset dispatch panel** | Card/grid per asset: state (SoC / CSS / output), recommended action, expected margin, constraint flag |
| **Grid & frequency panel** | Frequency gauge + aFRR/mFRR signal; reserve obligation |
| **Market gate panel** | Per-market gate countdowns + order-book depth; closing-soon emphasis |
| **Event & REMIT feed** | Ranked event list with type, zone, capacity, impact, severity |
| **Trading copilot** | Top recommendation card: action, rationale, expected € impact, confidence, linked event; accept/reject (demo: status only) |
| **Alerts & shift handover** | Open alerts + handover notes |
| **Footnote** | Selected trade date/interval only; illustrative data; recommendations are decision support |
| **Presenter guide** | Problem → cross-desk aggregation → story → zones walk-through → copilot → who uses |

### Presenter guide (in-app modal)

Business narrative for demos — in the page module:

| Section | Message |
|---|---|
| What problem this solves | Run and co-optimize the whole physical book live; act on the highest-value dispatch; hand over cleanly |
| How this aggregates the desk | Reads squaring + imbalance (01) and DSR dispatch (03); adds dispatch, frequency, gates, events, copilot |
| Story to tell | A 900 MW trip hits the feed → balance flips short → dispatch panel says discharge battery + bid DSR → copilot drafts the play with reasoning → operator accepts → P&L holds |
| "Now" toolbar | Trade date, interval cursor, zone, refresh |
| Balance & dispatch | Net position, per-asset action, expected margin, constraints |
| Grid, gates, events | Frequency/aFRR, gate countdowns, REMIT impact |
| Trading copilot | Agentic supervisor (classify → retrieve → query → recommend); operator keeps the decision |
| Who uses this view | Shift operators, intraday traders, dispatch/asset ops, risk |
| AI use case (optional close) | Mosaic AI dispatch policy + Agent Bricks copilot + Lakehouse Monitoring |

| Workflow intent | UI zone |
|---|---|
| Am I balanced? | Balance ribbon + status banner |
| What does each asset do? | Asset dispatch panel |
| Grid short/long, am I called? | Grid & frequency panel |
| Time to act / liquidity | Market gate panel |
| What changed? | Event & REMIT feed |
| What's the play and why? | Trading copilot |
| Shift handover | Alerts & handover |

### Empty and error states

| Condition | Message / behaviour |
|---|---|
| No warehouse selected | Prompt to select a running warehouse (no mock data) |
| No data | Prompt to run `energy_trading_demo_data` (notebooks **01 → 02**, plus **03** for DSR contribution) |
| DSR dispatch missing | Degrade gracefully: show balance from squaring only; note DSR contribution unavailable |
| Query failure | Show error text; do not fabricate zones |

### Widget-to-dataset binding

| UI zone | Primary datasets | Key fields |
|---|---|---|
| Status banner | `short_term_gold_control_tower_summary` | `headline`, `balance_state`, `pnl_since_shift_eur`, `n_open_alerts` |
| Balance ribbon | `short_term_gold_portfolio_balance` | `interval_start`, `net_position_mw`, `system_balance_direction`, `projected_cashout_eur` |
| Asset dispatch panel | `short_term_gold_asset_dispatch` | `asset_id`, `recommended_action`, `soc_pct`, `clean_spark_spread_eur`, `expected_margin_eur`, `constraint_flag` |
| Grid & frequency | `short_term_silver_grid_frequency` | `frequency_hz`, `afrr_signal_mw`, `signal_state`, `reserve_obligation_mw` |
| Market gates | `short_term_silver_market_gates` | `market`, `minutes_to_gate`, `order_book_depth_mw`, `gate_status` |
| Event feed | `short_term_gold_remit_events` | `event_type`, `affected_zone`, `capacity_mw`, `impact_eur_mwh`, `severity` |
| Trading copilot | `short_term_gold_copilot_recommendations` | `recommendation`, `rationale`, `expected_pnl_impact_eur`, `confidence`, `linked_event_id` |
| Alerts & handover | `short_term_gold_control_tower_summary` | `n_open_alerts`, `n_critical_events`, `handover_notes`, `shift_start_ts` |
| Trade-date / interval list | `short_term_dim_intervals` | `DISTINCT delivery_date`, `interval_start` |

---

## Relationships

| Direction | Dependency |
|---|---|
| **Upstream** | **01** — `short_term_gold_squaring_actions`, `short_term_gold_imbalance_exposure`, shared dimensions; **03** — `short_term_gold_dsr_dispatch` |
| **Downstream** | None — this is the operator's aggregated view (the top of the stack) |
| **Shared** | Consumes `short_term_dim_zones`, `short_term_dim_assets`, `short_term_dim_intervals` from 01 |

The control tower is the **aggregator**: breaking changes to 01's squaring/imbalance grain or 03's dispatch grain cascade here. Frequency, gates, events, and copilot tables are owned by this capability.

## Out of scope

- True real-time streaming in the demo (batch gold with `snapshot_ts`; streaming pattern documented)
- Live aFRR/mFRR market connectivity and real TSO activation signals
- Production Mosaic AI policy training (recommended actions are illustrative / surrogate)
- Live agent execution against markets — the copilot is **decision support**; the operator acts
- In-app mock data (see [`instructions.md`](./instructions.md))
