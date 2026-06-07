# 04 — Natural language prompt-desk intelligence (Genie)

> Parent brief: [`main.md`](./main.md) (Use Case 4). Implementation rules: [`instructions.md`](./instructions.md).

## Summary

Intraday traders and operators ask plain-English questions over the **same gold tables** built in notebooks 01–03 (with 02 aggregating last). Notebook 04 provisions the Genie Space **Energy Trading Genie - Short Term** and registers **Unity Catalog metric views** for KPI-style questions. Sample questions and example SQL are embedded in the Genie Space config only (`genie_space_config.py`). The notebook prints `space_id` for deep links or env configuration.

## Databricks fit

- **Databricks Genie** — Space created/updated via REST (`POST` / `PATCH /api/2.0/genie/spaces`) or SDK when available, using `serialized_space` from [`genie_space_config.py`](../notebooks/genie_space_config.py).
- **Unity Catalog metric views** (`WITH METRICS`) on near-delivery, control-tower, and DSR gold tables (DBR 17.2+).
- **Unity Catalog governance** — Genie respects table/column access on positions, DSR owners, and settlement.
- **Lineage** — answers trace to `short_term_gold_*` and dimension tables via UC lineage.

## Notebook

[`../notebooks/04_trader_insights_genie.ipynb`](../notebooks/04_trader_insights_genie.ipynb):

1. Asserts notebooks 01 → 03 → 02 tables exist.
2. Creates metric views `mv_st_*` (best-effort if cluster supports them).
3. Creates or updates Genie Space **Energy Trading Genie - Short Term** (prints `space_id`).
4. Applies UC comments from `uc_table_comments.py`.

**Widget:** `warehouse_id` — optional SQL warehouse id; auto-picks a running warehouse if blank.

## Genie Space scope

**Title:** `Energy Trading Genie - Short Term`

### Base tables (21)

| Area | Tables |
|------|--------|
| Dimensions | `short_term_dim_zones`, `short_term_dim_assets`, `short_term_dim_intervals`, `short_term_dim_dsr_assets`, `short_term_dim_dsr_owners` |
| Near delivery (01) | `short_term_gold_squaring_actions`, `short_term_gold_near_delivery_summary`, `short_term_gold_imbalance_exposure`, `short_term_gold_backtest_runs` |
| Control tower (02) | `short_term_gold_portfolio_balance`, `short_term_gold_asset_dispatch`, `short_term_silver_grid_frequency`, `short_term_silver_market_gates`, `short_term_gold_remit_events`, `short_term_gold_copilot_recommendations`, `short_term_gold_control_tower_summary` |
| DSR (03) | `short_term_silver_dsr_availability`, `short_term_gold_dsr_bid_stack`, `short_term_gold_dsr_dispatch`, `short_term_gold_dsr_settlement`, `short_term_gold_dsr_summary` |

### Metric views (5)

| View | Source table |
|------|----------------|
| `mv_st_near_delivery_summary` | `short_term_gold_near_delivery_summary` |
| `mv_st_squaring_actions` | `short_term_gold_squaring_actions` |
| `mv_st_portfolio_balance` | `short_term_gold_portfolio_balance` |
| `mv_st_dsr_summary` | `short_term_gold_dsr_summary` |
| `mv_st_dsr_dispatch` | `short_term_gold_dsr_dispatch` |

Text instructions, sample questions, and example SQL live in `genie_space_config.py` and are embedded in the serialized Space config.

## App UI (Dash)

Page route: `/short-term/insights` — [`app/pages/short_term_insights.py`](../../../app/pages/short_term_insights.py).

| Widget | Status | Notes |
|---|---|---|
| Title, summary, Genie callout, presenter guide | Done | |
| Genie Space dropdown (title prefix filter) | Done | Lists spaces starting with **Energy Trading Genie - Short Term**; shows description + sample questions. |
| Context KPIs, SQL widgets | Planned | `short_term_gold_near_delivery_summary`, `short_term_gold_control_tower_summary`. |

## Relationships

- **Upstream:** all gold/dim tables from notebooks 01, 03, and 02 (control tower aggregates 01 + 03).
- **Complements:** in-dash trading copilot on `/short-term/control-tower` (`short_term_gold_copilot_recommendations`) — curated recommendations vs ad-hoc Genie SQL.
- **Downstream:** optional Conversation API using `space_id` from notebook logs or env.

## Out of scope

- Custom LLM hosting; voice bots outside Genie.
- Replacing the control-tower copilot with Genie-only UX.

## Implementation status

| Item | Status |
|------|--------|
| `genie_space_config.py` | Done |
| Notebook 04 | Done |
| Dash `/short-term/insights` (header + presenter guide) | Done |
| Demo job task `st04_trader_insights` | Done |
