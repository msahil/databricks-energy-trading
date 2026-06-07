# Databricks notebook source
"""
Unity Catalog table and column COMMENTs for short-term trading demo tables.

Coding agents: read TABLE_METADATA for semantics, grain, and lineage hints.
Notebooks load this file with exec(open(...).read(), globals()) then call apply_*_comments().

Capabilities:
- 01 Trading near delivery  (owns shared dimensions)
- 02 24/7 Operations & Live Dispatch (control tower; aggregates 01 + 03)
- 03 DSR & Market Access
- 04 Trader insights (Genie) — metric views mv_st_*
"""

from __future__ import annotations

from typing import Any


def _sql_literal(value: str) -> str:
    return "'" + (value or "").replace("'", "''") + "'"


def apply_table_comments(
    spark: Any,
    catalog: str,
    schema: str,
    table: str,
    table_comment: str,
    column_comments: dict[str, str],
) -> None:
    """Set COMMENT ON TABLE / COLUMN in Unity Catalog (idempotent)."""
    fq = f"`{catalog}`.`{schema}`.`{table}`"
    spark.sql(f"COMMENT ON TABLE {fq} IS {_sql_literal(table_comment)}")
    for column, description in column_comments.items():
        spark.sql(f"COMMENT ON COLUMN {fq}.`{column}` IS {_sql_literal(description)}")


def _table_exists(spark: Any, catalog: str, schema: str, name: str) -> bool:
    fq = f"`{catalog}`.`{schema}`.`{name}`"
    return bool(spark.catalog.tableExists(fq))


def _apply_bundle(
    spark: Any,
    catalog: str,
    schema: str,
    names: tuple[str, ...],
    *,
    skip_missing: bool = False,
) -> None:
    for name in names:
        if skip_missing and not _table_exists(spark, catalog, schema, name):
            continue
        meta = TABLE_METADATA[name]
        apply_table_comments(spark, catalog, schema, name, meta["table"], meta["columns"])


# fmt: off
TABLE_METADATA: dict[str, dict[str, Any]] = {
    # ---------------------------------------------------------------- #
    # Shared dimensions (owned by capability 01)
    # ---------------------------------------------------------------- #
    "short_term_dim_zones": {
        "table": "Shared dimension: European power bidding zones for the short-term desk (capability 01 owner). Grain: one row per zone_code. Used by 02 and 03.",
        "columns": {
            "zone_code": "Primary key. ISO-style zone: DE, NL, FR, BE, AT.",
            "country": "Country name for reporting.",
            "tso_name": "Transmission System Operator(s) for the zone.",
            "imbalance_area": "TSO imbalance / control area label.",
            "eic_code": "Illustrative EIC bidding-zone identifier.",
            "currency": "Trading currency; demo uses EUR only.",
        },
    },
    "short_term_dim_assets": {
        "table": "Shared dimension: the physical 1,000 MW Central-Europe portfolio (CCGT, wind, solar, battery). Grain: one row per asset_id. Used by 02 dispatch.",
        "columns": {
            "asset_id": "Primary key, e.g. CCGT_DE_001, WIND_DE_001, SOLAR_DE_001, BATT_DE_001.",
            "asset_type": "CCGT, WIND_ONSHORE, SOLAR_PV, or BATTERY.",
            "nameplate_mw": "Rated power in MW.",
            "zone_code": "FK to short_term_dim_zones.",
            "efficiency": "CCGT thermal efficiency (e.g. 0.55); null for non-thermal.",
            "emission_factor_tco2_mwh": "CCGT carbon emission factor (e.g. 0.364); null otherwise.",
            "energy_capacity_mwh": "Battery energy capacity in MWh; null otherwise.",
            "is_dispatchable": "True for CCGT/battery/hydro; false for wind/solar.",
            "annotation": "Free-text note, e.g. 'fast start-stop', '2h duration battery'.",
        },
    },
    "short_term_dim_intervals": {
        "table": "Shared time spine: 15-minute delivery intervals per trading day (capability 01 owner). Grain: one row per interval_start. Used by 02 and 03.",
        "columns": {
            "delivery_date": "Trading / delivery day.",
            "interval_start": "Interval start timestamp (15-minute grain).",
            "interval_end": "Interval end timestamp.",
            "interval_index": "1..96 within the day.",
            "hour": "Hour of day 0..23.",
            "is_peak": "True within the peak-load window.",
            "solar_window": "True within the midday solar-peak window (negative-price risk).",
        },
    },
    # ---------------------------------------------------------------- #
    # Capability 01 — trading near delivery
    # ---------------------------------------------------------------- #
    "short_term_bronze_weather_obs": {
        "table": "Bronze: streamed weather observations / re-forecast inputs. Grain: forecast_ts x zone_code x interval_start.",
        "columns": {
            "ingestion_ts": "UTC landing time.",
            "forecast_ts": "Re-forecast issue time (latest = live).",
            "source": "ECMWF, GFS, VENDOR_X, or SATELLITE.",
            "zone_code": "FK to short_term_dim_zones.",
            "interval_start": "Target 15-minute interval.",
            "wind_speed_ms": "Forecast wind speed (m/s).",
            "solar_irradiance_wm2": "Forecast irradiance (W/m^2).",
            "temperature_c": "Forecast temperature (Celsius).",
            "cloud_cover_pct": "Cloud cover 0-100.",
        },
    },
    "short_term_bronze_scada_telemetry": {
        "table": "Bronze: live asset SCADA telemetry. Grain: telemetry_ts x asset_id.",
        "columns": {
            "ingestion_ts": "UTC landing time.",
            "telemetry_ts": "Measurement time.",
            "asset_id": "FK to short_term_dim_assets.",
            "actual_output_mw": "Metered output in MW.",
            "availability_pct": "Asset availability 0-100.",
            "status": "RUNNING, CURTAILED, or OUTAGE.",
        },
    },
    "short_term_silver_generation_forecast": {
        "table": "Silver: re-forecast vs actual per asset per interval. Grain: forecast_ts x asset_id x interval_start.",
        "columns": {
            "delivery_date": "Trading day.",
            "interval_start": "Target interval.",
            "forecast_ts": "Re-forecast issue time (latest = live).",
            "asset_id": "FK to short_term_dim_assets.",
            "zone_code": "Denormalised zone.",
            "forecast_mw": "Current forecast output.",
            "prev_forecast_mw": "Prior re-forecast output.",
            "actual_mw": "Metered output; null for future intervals.",
            "forecast_deviation_mw": "forecast_mw minus prev_forecast_mw.",
            "deviation_severity": "OK, WATCH, or SEVERE.",
        },
    },
    "short_term_silver_nominations": {
        "table": "Silver: commercial nominations / schedule per zone per interval, including hedge handover from the curve desk. Grain: delivery_date x zone_code x interval_start.",
        "columns": {
            "delivery_date": "Trading day.",
            "interval_start": "Interval.",
            "zone_code": "FK to short_term_dim_zones.",
            "nominated_mw": "Scheduled net position (signed).",
            "hedge_mw": "Long-term hedge handed over from the curve desk.",
            "source": "SCHEDULE or HEDGE_HANDOVER.",
        },
    },
    "short_term_gold_squaring_actions": {
        "table": "Gold (primary): residual long/short delta and recommended squaring action per interval before gate close. Grain: delivery_date x zone_code x interval_start (latest forecast_ts). Consumed by 02 control tower.",
        "columns": {
            "delivery_date": "Trading day.",
            "interval_start": "Interval.",
            "interval_index": "1..96.",
            "zone_code": "FK to short_term_dim_zones.",
            "forecast_ts": "Re-forecast feeding this action.",
            "forecast_gen_mw": "Total renewable forecast for the zone.",
            "nominated_mw": "Net commercial nomination.",
            "net_delta_mw": "Long(+)/short(-) residual to square.",
            "recommended_side": "BUY, SELL, or FLAT.",
            "recommended_mw": "Suggested squaring volume.",
            "expected_price_eur_mwh": "Indicative intraday clearing price.",
            "gate_close_ts": "XBID/SIDC gate close for this interval.",
            "minutes_to_gate": "Countdown at forecast_ts.",
            "gate_status": "OPEN, CLOSING, or CLOSED.",
        },
    },
    "short_term_gold_near_delivery_summary": {
        "table": "Gold: headline near-delivery KPIs per trading day. Grain: delivery_date x snapshot_ts.",
        "columns": {
            "delivery_date": "Trading day.",
            "snapshot_ts": "As-last-updated time.",
            "headline": "Primary desk action message.",
            "net_open_position_mw": "Sum of unsquared delta across open intervals.",
            "n_intervals_open": "Intervals still tradable.",
            "n_intervals_closing": "Intervals inside the gate-closing window.",
            "n_severe_deviations": "Assets in SEVERE forecast deviation.",
            "projected_cashout_eur": "Total projected cash-out if unsquared.",
            "system_balance_direction": "Net grid LONG or SHORT.",
            "next_gate_close_ts": "Soonest gate close across zones.",
        },
    },
    "short_term_gold_imbalance_exposure": {
        "table": "Gold: imbalance and cash-out projection per interval. Grain: delivery_date x zone_code x interval_start. Consumed by 02 control tower.",
        "columns": {
            "delivery_date": "Trading day.",
            "interval_start": "Interval.",
            "zone_code": "FK to short_term_dim_zones.",
            "nominated_mw": "What was promised.",
            "metered_mw": "What assets actually produced; null for future intervals.",
            "net_imbalance_mw": "metered minus nominated (signed).",
            "system_balance_direction": "TSO grid LONG or SHORT.",
            "imbalance_price_eur_mwh": "Illustrative single/dual cash-out price.",
            "projected_cashout_eur": "net_imbalance_mw x imbalance_price (signed cost).",
            "exposure_severity": "OK, WATCH, or BREACH.",
        },
    },
    "short_term_gold_backtest_runs": {
        "table": "Gold: backtested squaring strategy variants over historical intervals (MLflow-tracked). Grain: run_id x strategy.",
        "columns": {
            "run_id": "MLflow run id or synthetic surrogate.",
            "strategy": "EARLY_SQUARE, WAIT_FOR_GATE, THRESHOLD_DEVIATION, or BASELINE_NO_TRADE.",
            "backtest_start_date": "First replayed delivery day.",
            "backtest_end_date": "Last replayed delivery day.",
            "n_intervals": "Intervals replayed.",
            "realized_pnl_eur": "Strategy P&L over the window.",
            "cashout_avoided_eur": "Cash-out saved vs BASELINE_NO_TRADE.",
            "hit_rate_pct": "Percent of intervals where the rule improved P&L.",
            "avg_minutes_before_gate": "Mean lead time of squaring trades.",
            "is_recommended": "True for the best variant shown on the page.",
        },
    },
    # ---------------------------------------------------------------- #
    # Capability 02 — control tower
    # ---------------------------------------------------------------- #
    "short_term_silver_grid_frequency": {
        "table": "Silver: live grid frequency and balancing signals. Grain: snapshot_ts x zone_code.",
        "columns": {
            "snapshot_ts": "Measurement time.",
            "delivery_date": "Trading day.",
            "interval_start": "Interval.",
            "zone_code": "FK to short_term_dim_zones.",
            "frequency_hz": "Grid frequency (~50.0 Hz).",
            "frequency_deviation_mhz": "Deviation from 50 Hz in mHz.",
            "afrr_signal_mw": "aFRR activation signal (signed).",
            "mfrr_signal_mw": "mFRR activation signal (signed).",
            "reserve_obligation_mw": "Our prequalified reserve commitment.",
            "signal_state": "NEUTRAL, CALL_UP, or CALL_DOWN.",
        },
    },
    "short_term_silver_market_gates": {
        "table": "Silver: gate countdowns and liquidity per market per zone. Grain: snapshot_ts x market x zone_code.",
        "columns": {
            "snapshot_ts": "As-last-updated time.",
            "delivery_date": "Trading day.",
            "market": "DAY_AHEAD, INTRADAY_AUCTION, XBID_CONTINUOUS, or AFRR.",
            "zone_code": "FK to short_term_dim_zones.",
            "next_gate_close_ts": "Next gate close timestamp.",
            "minutes_to_gate": "Countdown in minutes.",
            "order_book_depth_mw": "Liquidity at touch (MW).",
            "best_bid_eur_mwh": "Top of book bid.",
            "best_ask_eur_mwh": "Top of book ask.",
            "gate_status": "OPEN, CLOSING, or CLOSED.",
        },
    },
    "short_term_gold_portfolio_balance": {
        "table": "Gold: control-tower balance ribbon aggregating squaring (01) and DSR dispatch (03). Grain: delivery_date x interval_start x snapshot_ts.",
        "columns": {
            "delivery_date": "Trading day.",
            "interval_start": "Interval.",
            "snapshot_ts": "As-last-updated time.",
            "net_position_mw": "Portfolio net long(+)/short(-) incl. squaring + DSR.",
            "squaring_delta_mw": "Contribution from 01 squaring actions.",
            "dsr_contribution_mw": "Contribution from 03 DSR dispatch.",
            "system_balance_direction": "TSO grid LONG or SHORT.",
            "projected_cashout_eur": "If left unbalanced into delivery.",
            "balance_state": "BALANCED, WATCH, or EXPOSED.",
        },
    },
    "short_term_gold_asset_dispatch": {
        "table": "Gold: per-asset live state plus Mosaic AI recommended action. Grain: delivery_date x interval_start x asset_id x snapshot_ts.",
        "columns": {
            "delivery_date": "Trading day.",
            "interval_start": "Interval.",
            "snapshot_ts": "As-last-updated time.",
            "asset_id": "FK to short_term_dim_assets.",
            "asset_type": "Denormalised asset type.",
            "current_output_mw": "Live metered output.",
            "soc_pct": "Battery state of charge; null for non-battery.",
            "cycle_budget_remaining": "Battery daily cycles remaining; null otherwise.",
            "clean_spark_spread_eur": "CCGT clean spark spread; null otherwise.",
            "recommended_action": "CHARGE, HOLD, DISCHARGE, RAMP_UP, RAMP_DOWN, BID_AFRR, or IDLE.",
            "expected_margin_eur": "Expected euro margin from the action this interval.",
            "policy_confidence": "0-1 confidence from the serving model.",
            "constraint_flag": "OK, SOC_LIMIT, RAMP_LIMIT, or MIN_RUNTIME.",
        },
    },
    "short_term_gold_remit_events": {
        "table": "Gold: streamed REMIT / outage / weather-shock events with impact scoring. Grain: event_id. raw_message is the Vector Search source.",
        "columns": {
            "event_id": "Primary key.",
            "event_ts": "Broadcast time.",
            "delivery_date": "Trading day affected.",
            "event_type": "THERMAL_TRIP, INTERCONNECTOR_OUTAGE, WIND_RAMP_DOWN, SOLAR_SHOCK, or NUCLEAR_TRIP.",
            "affected_zone": "FK to short_term_dim_zones.",
            "asset_or_unit": "Affected unit label (illustrative).",
            "capacity_mw": "Capacity removed/added (MW).",
            "impact_eur_mwh": "Estimated price impact.",
            "impact_horizon_hours": "Expected duration of impact.",
            "severity": "INFO, WATCH, or CRITICAL.",
            "raw_message": "Unstructured REMIT text (Vector Search source).",
        },
    },
    "short_term_gold_copilot_recommendations": {
        "table": "Gold: agentic trading-copilot recommendations linked to events. Grain: recommendation_id. Decision support only.",
        "columns": {
            "recommendation_id": "Primary key.",
            "generated_ts": "When the agent produced it.",
            "delivery_date": "Trading day.",
            "linked_event_id": "FK to short_term_gold_remit_events (nullable).",
            "recommendation": "Action text drafted by the agent.",
            "rationale": "Grounded reasoning with cited figures.",
            "expected_pnl_impact_eur": "Estimated euro benefit.",
            "confidence": "0-1 supervisor confidence.",
            "agent_trace": "Which sub-agents contributed (classify/retrieve/query).",
            "status": "PROPOSED, ACCEPTED, or REJECTED.",
        },
    },
    "short_term_gold_control_tower_summary": {
        "table": "Gold: control-tower header banner, P&L, alerts, and shift handover. Grain: delivery_date x snapshot_ts.",
        "columns": {
            "delivery_date": "Trading day.",
            "snapshot_ts": "As-last-updated time.",
            "headline": "Primary ops message.",
            "pnl_since_shift_eur": "P&L since shift start.",
            "net_position_mw": "Current portfolio net position.",
            "balance_state": "BALANCED, WATCH, or EXPOSED.",
            "n_open_alerts": "Lakehouse-monitoring alerts open.",
            "n_critical_events": "CRITICAL events in the window.",
            "n_assets_actionable": "Assets with a non-HOLD/IDLE recommendation.",
            "top_copilot_recommendation_id": "Highest-confidence open recommendation.",
            "shift_start_ts": "Current shift start.",
            "handover_notes": "Open actions for the next shift.",
        },
    },
    # ---------------------------------------------------------------- #
    # Capability 03 — DSR & market access
    # ---------------------------------------------------------------- #
    "short_term_dim_dsr_assets": {
        "table": "Dimension: VPP asset registry of distributed flexible assets (capability 03 owner). Grain: one row per dsr_asset_id.",
        "columns": {
            "dsr_asset_id": "Primary key, e.g. EVDEPOT_DE_0142.",
            "owner_id": "FK to short_term_dim_dsr_owners.",
            "asset_type": "INDUSTRIAL_LOAD, EV_DEPOT, HEAT_PUMP, or BTM_BATTERY.",
            "zone_code": "FK to short_term_dim_zones.",
            "max_flex_up_mw": "Max curtailable / dischargeable power.",
            "max_flex_down_mw": "Max absorbable / increasable load.",
            "response_time_s": "Activation response time (seconds).",
            "min_runtime_min": "Minimum sustain duration (minutes).",
            "prequalified_markets": "CSV of AFRR, MFRR, INTRADAY the asset qualifies for.",
        },
    },
    "short_term_dim_dsr_owners": {
        "table": "Dimension: third-party asset owners (Delta Sharing settlement recipients). Grain: one row per owner_id.",
        "columns": {
            "owner_id": "Primary key.",
            "owner_name": "Illustrative organisation name.",
            "owner_segment": "INDUSTRIAL, MOBILITY, RESIDENTIAL_AGG, or COMMERCIAL.",
            "share_pct": "Revenue share to the owner (e.g. 0.80).",
            "settlement_currency": "EUR.",
        },
    },
    "short_term_bronze_submeter_telemetry": {
        "table": "Bronze: high-cardinality submeter feed from the VPP fleet. Grain: telemetry_ts x dsr_asset_id.",
        "columns": {
            "ingestion_ts": "UTC landing time.",
            "telemetry_ts": "Measurement time.",
            "dsr_asset_id": "FK to short_term_dim_dsr_assets.",
            "consumption_mw": "Live load (positive = consuming).",
            "baseline_mw": "Expected load absent any signal.",
            "soc_pct": "BTM battery SoC; null otherwise.",
            "status": "ONLINE, OFFLINE, or DISPATCHED.",
        },
    },
    "short_term_silver_dsr_availability": {
        "table": "Silver: per-asset (aggregable) flexibility per interval with Mosaic AI baseline. Grain: delivery_date x dsr_asset_id x interval_start.",
        "columns": {
            "delivery_date": "Trading day.",
            "interval_start": "Interval.",
            "dsr_asset_id": "FK to short_term_dim_dsr_assets.",
            "owner_id": "Denormalised owner.",
            "asset_type": "Denormalised asset type.",
            "zone_code": "Denormalised zone.",
            "baseline_mw": "Counterfactual baseline (Mosaic AI).",
            "available_up_mw": "Flex up (reduce load / discharge).",
            "available_down_mw": "Flex down (increase load / charge).",
            "direction": "UP, DOWN, BOTH, or NONE.",
            "confidence": "0-1 forecast confidence.",
        },
    },
    "short_term_gold_dsr_bid_stack": {
        "table": "Gold: aggregated prequalified bid stack per market per interval. Grain: delivery_date x market x zone_code x interval_start.",
        "columns": {
            "delivery_date": "Trading day.",
            "interval_start": "Interval.",
            "market": "AFRR, MFRR, or INTRADAY.",
            "zone_code": "FK to short_term_dim_zones.",
            "qualified_mw": "Aggregate prequalified volume.",
            "n_assets": "Assets in the stack.",
            "bid_price_eur_mwh": "Stack offer price.",
            "prequalification_status": "QUALIFIED, PARTIAL, or BELOW_MIN_SIZE.",
            "min_size_mw": "Market minimum bid size.",
        },
    },
    "short_term_gold_dsr_dispatch": {
        "table": "Gold: dispatched volume and verified delivery. Grain: delivery_date x market x zone_code x interval_start. Feeds the 02 control-tower balance ribbon.",
        "columns": {
            "delivery_date": "Trading day.",
            "interval_start": "Interval.",
            "market": "AFRR, MFRR, or INTRADAY.",
            "zone_code": "FK to short_term_dim_zones.",
            "signal_trigger": "NEGATIVE_PRICE, SCARCITY, or FREQUENCY.",
            "dispatched_mw": "Instructed volume (signed: + discharge/curtail, - absorb).",
            "delivered_mw": "Verified delivered volume.",
            "delivery_ratio": "delivered / dispatched.",
            "clearing_price_eur_mwh": "Market clearing price.",
            "verification_status": "VERIFIED, UNDER_DELIVERED, or PENDING.",
        },
    },
    "short_term_gold_dsr_settlement": {
        "table": "Gold: per-owner settlement (Delta Sharing target). Grain: delivery_date x owner_id.",
        "columns": {
            "delivery_date": "Trading day.",
            "owner_id": "FK to short_term_dim_dsr_owners.",
            "owner_name": "Denormalised owner name.",
            "total_delivered_mwh": "Verified energy delivered.",
            "market_revenue_eur": "Gross market value captured.",
            "owner_payment_eur": "Owner share (market_revenue x share_pct).",
            "aggregator_fee_eur": "Desk retained fee.",
            "n_assets_dispatched": "Owner assets activated.",
            "settlement_status": "SETTLED or PENDING.",
        },
    },
    "short_term_gold_dsr_summary": {
        "table": "Gold: headline DSR / market-access KPIs per trading day. Grain: delivery_date x snapshot_ts.",
        "columns": {
            "delivery_date": "Trading day.",
            "snapshot_ts": "As-last-updated time.",
            "headline": "Primary desk message.",
            "total_available_up_mw": "Peak flex-up available.",
            "total_available_down_mw": "Peak flex-down available.",
            "total_dispatched_mwh": "Energy dispatched in the window.",
            "total_market_revenue_eur": "Gross value captured.",
            "total_owner_payments_eur": "Paid to owners.",
            "avg_delivery_ratio": "Mean verified delivery ratio.",
            "n_assets_online": "Assets online in the fleet.",
            "n_owners": "Distinct owners settled.",
        },
    },
    "mv_st_near_delivery_summary": {
        "table": "Metric view: near-delivery desk KPIs on short_term_gold_near_delivery_summary (Genie UC4).",
        "columns": {},
    },
    "mv_st_squaring_actions": {
        "table": "Metric view: squaring and gate KPIs on short_term_gold_squaring_actions (Genie UC4).",
        "columns": {},
    },
    "mv_st_portfolio_balance": {
        "table": "Metric view: control-tower balance KPIs on short_term_gold_portfolio_balance (Genie UC4).",
        "columns": {},
    },
    "mv_st_dsr_summary": {
        "table": "Metric view: DSR desk headline KPIs on short_term_gold_dsr_summary (Genie UC4).",
        "columns": {},
    },
    "mv_st_dsr_dispatch": {
        "table": "Metric view: verified dispatch KPIs on short_term_gold_dsr_dispatch (Genie UC4).",
        "columns": {},
    },
}
# fmt: on

_NOTEBOOK_01 = (
    "short_term_dim_zones",
    "short_term_dim_assets",
    "short_term_dim_intervals",
    "short_term_bronze_weather_obs",
    "short_term_bronze_scada_telemetry",
    "short_term_silver_generation_forecast",
    "short_term_silver_nominations",
    "short_term_gold_squaring_actions",
    "short_term_gold_near_delivery_summary",
    "short_term_gold_imbalance_exposure",
    "short_term_gold_backtest_runs",
)

_NOTEBOOK_02 = (
    "short_term_silver_grid_frequency",
    "short_term_silver_market_gates",
    "short_term_gold_portfolio_balance",
    "short_term_gold_asset_dispatch",
    "short_term_gold_remit_events",
    "short_term_gold_copilot_recommendations",
    "short_term_gold_control_tower_summary",
)

_NOTEBOOK_03 = (
    "short_term_dim_dsr_assets",
    "short_term_dim_dsr_owners",
    "short_term_bronze_submeter_telemetry",
    "short_term_silver_dsr_availability",
    "short_term_gold_dsr_bid_stack",
    "short_term_gold_dsr_dispatch",
    "short_term_gold_dsr_settlement",
    "short_term_gold_dsr_summary",
)


def apply_short_term_notebook_01_comments(spark: Any, catalog: str, schema: str) -> None:
    _apply_bundle(spark, catalog, schema, _NOTEBOOK_01)


def apply_short_term_notebook_02_comments(spark: Any, catalog: str, schema: str) -> None:
    _apply_bundle(spark, catalog, schema, _NOTEBOOK_02)


def apply_short_term_notebook_03_comments(spark: Any, catalog: str, schema: str) -> None:
    _apply_bundle(spark, catalog, schema, _NOTEBOOK_03)


_NOTEBOOK_04 = (
    "mv_st_near_delivery_summary",
    "mv_st_squaring_actions",
    "mv_st_portfolio_balance",
    "mv_st_dsr_summary",
    "mv_st_dsr_dispatch",
)


def apply_short_term_notebook_04_comments(spark: Any, catalog: str, schema: str) -> None:
    """Metric view comments only when ``mv_st_*`` were created (DBR 17.2+)."""
    _apply_bundle(spark, catalog, schema, _NOTEBOOK_04, skip_missing=True)


def apply_all_short_term_comments(spark: Any, catalog: str, schema: str) -> None:
    """Apply every short-term table comment (after full demo job)."""
    for name in TABLE_METADATA:
        if not _table_exists(spark, catalog, schema, name):
            continue
        meta = TABLE_METADATA[name]
        apply_table_comments(spark, catalog, schema, name, meta["table"], meta["columns"])
