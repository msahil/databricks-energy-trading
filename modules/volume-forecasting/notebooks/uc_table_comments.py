# Databricks notebook source
"""
Unity Catalog table and column COMMENTs for volume forecasting demo tables.

Coding agents: read TABLE_METADATA for semantics, grain, and lineage hints.
Notebooks load this file with exec(open(...).read(), globals()) then call
apply_volume_forecast_notebook_0X_comments().

Capabilities (see ../specifications):
- 04 Smart Metering            (owns shared dimensions + curated meter profile)
- 01 Customer Consumption · Short Term
- 02 Customer Consumption · Long Term
- 03 Industry Involvement
- 05 Wind Forecasting          (owns wind asset registry)
- 06 Solar Forecasting         (owns solar asset registry; BTM-PV reconciliation)
- 07 Publication & Net-Volume Reconciliation  (official source of truth)
- 08 Forecast Accuracy & Value (error -> euros; model governance)

Build / run order: 04 -> (01, 02, 03) + (05, 06) -> 07 -> 08.
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
    # ================================================================== #
    # 04 Smart Metering — shared dimensions + curated profile (backbone)
    # ================================================================== #
    "volume_forecast_dim_zones": {
        "table": "Shared dimension: European power bidding zones for volume forecasting (capability 04 owner). Grain: one row per zone_code. Used by 01-03, 05-08.",
        "columns": {
            "zone_code": "Primary key. ISO-style zone: DE, NL, FR, BE, AT.",
            "country": "Country name for reporting.",
            "tso_name": "Transmission System Operator(s) for the zone.",
            "control_area": "TSO control / imbalance area label.",
            "eic_code": "Illustrative EIC bidding-zone identifier.",
            "currency": "Trading currency; demo uses EUR only.",
        },
    },
    "volume_forecast_dim_segments": {
        "table": "Shared dimension: customer segments behind the meter (capability 04 owner). Grain: one row per segment_code. Used by 01, 02.",
        "columns": {
            "segment_code": "Primary key: RES, RES_PV, RES_EV, SME, CNI.",
            "segment_name": "Human-readable segment label.",
            "customer_class": "RESIDENTIAL, COMMERCIAL, or INDUSTRIAL.",
            "has_btm_pv": "True if the segment carries behind-the-meter solar.",
            "has_ev": "True if the segment carries EV charging load.",
            "default_tariff": "Illustrative tariff profile code.",
        },
    },
    "volume_forecast_dim_intervals": {
        "table": "Shared time spine: 15-minute intervals per day (capability 04 owner). Grain: one row per interval_start. Used across the module.",
        "columns": {
            "delivery_date": "Calendar / delivery day.",
            "interval_start": "Interval start timestamp (15-minute grain).",
            "interval_end": "Interval end timestamp.",
            "interval_index": "1-96 within the day.",
            "hour": "Hour of day 0-23.",
            "day_type": "WEEKDAY, WEEKEND, or HOLIDAY.",
            "season": "WINTER, SPRING, SUMMER, or AUTUMN.",
            "is_peak": "True in the peak-load window.",
            "solar_window": "True in the midday solar-peak window.",
        },
    },
    "volume_forecast_bronze_meter_reads": {
        "table": "Bronze: raw AMI interval reads (synthetic sample). Grain: read_ts x meter_id. Aggregated upward; individual meters never exposed downstream.",
        "columns": {
            "ingestion_ts": "Auto Loader landing time.",
            "read_ts": "Interval the read covers.",
            "meter_id": "Synthetic surrogate meter id.",
            "segment_code": "FK to volume_forecast_dim_segments.",
            "zone_code": "FK to volume_forecast_dim_zones.",
            "consumption_kwh": "Imported energy in the interval.",
            "export_kwh": "Exported (behind-the-meter PV) energy.",
            "read_quality": "OK, ESTIMATED, MISSING, or CORRUPT.",
        },
    },
    "volume_forecast_bronze_meter_events": {
        "table": "Bronze: meter lifecycle / data events. Grain: event_ts x meter_id.",
        "columns": {
            "ingestion_ts": "Landing time.",
            "event_ts": "Event time.",
            "meter_id": "Synthetic meter id.",
            "event_type": "GAP, LATE, TAMPER, RECONNECT, or FW_UPDATE.",
            "detail": "Free-text note.",
        },
    },
    "volume_forecast_silver_btm_pv": {
        "table": "Silver: behind-the-meter PV deducted from gross consumption. Grain: interval_start x zone_code x segment_code. Consumed by 01 and 06.",
        "columns": {
            "delivery_date": "Day.",
            "interval_start": "Interval.",
            "zone_code": "FK to volume_forecast_dim_zones.",
            "segment_code": "FK to volume_forecast_dim_segments.",
            "btm_pv_mw": "Estimated behind-the-meter PV generation (deducted from gross).",
            "n_pv_meters": "Meters with export in the interval.",
        },
    },
    "volume_forecast_silver_meter_profile": {
        "table": "Silver: curated, forecast-ready net load profile (capability 04 output). Grain: interval_start x zone_code x segment_code. Shared input to 01-03.",
        "columns": {
            "delivery_date": "Day.",
            "interval_start": "Interval.",
            "zone_code": "FK to volume_forecast_dim_zones.",
            "segment_code": "FK to volume_forecast_dim_segments.",
            "gross_load_mw": "Total imported demand.",
            "btm_pv_mw": "Behind-the-meter PV deducted.",
            "net_load_mw": "gross_load_mw - btm_pv_mw.",
            "n_meters": "Meters aggregated (kept above k-anonymity threshold).",
            "dq_status": "GOOD, IMPUTED, or SUSPECT.",
            "profile_version": "Curation version.",
            "as_of_ts": "When the profile was curated.",
        },
    },
    "volume_forecast_gold_metering_quality": {
        "table": "Gold: data-quality SLA rollup for the meter feed. Grain: delivery_date x zone_code x segment_code.",
        "columns": {
            "delivery_date": "Day.",
            "zone_code": "FK to volume_forecast_dim_zones.",
            "segment_code": "FK to volume_forecast_dim_segments.",
            "expected_reads": "Meters x intervals expected.",
            "received_reads": "Reads actually landed.",
            "completeness_pct": "received / expected * 100.",
            "late_read_pct": "Percent arriving after the interval closed.",
            "corrupt_read_pct": "Percent flagged CORRUPT / MISSING.",
            "imputed_intervals": "Intervals gap-filled.",
            "dq_status": "GOOD, WATCH, or BREACH.",
        },
    },

    # ================================================================== #
    # 01 Customer Consumption — Short Term
    # ================================================================== #
    "volume_forecast_bronze_weather_obs": {
        "table": "Bronze: weather drivers for short-term consumption. Grain: forecast_ts x zone_code x interval_start.",
        "columns": {
            "ingestion_ts": "Landing time.",
            "forecast_ts": "Weather forecast issue time.",
            "source": "ECMWF, GFS, ICON, or VENDOR_X.",
            "zone_code": "FK to volume_forecast_dim_zones.",
            "interval_start": "Target interval.",
            "temperature_c": "Forecast temperature.",
            "solar_irradiance_wm2": "Forecast irradiance (BTM PV driver).",
            "cloud_cover_pct": "Cloud cover 0-100.",
        },
    },
    "volume_forecast_silver_consumption_st": {
        "table": "Silver: probabilistic short-term consumption, climatological profile (04) shaped by weather. Grain: forecast_ts x zone_code x segment_code x interval_start. Two forecast vintages per interval (prev run + latest run); latest forecast_ts is live. actual_mw is realised on settled intervals (null in the future).",
        "columns": {
            "delivery_date": "Day.",
            "interval_start": "Target interval.",
            "forecast_ts": "Forecast run/issue time; two vintages per interval, latest = live.",
            "zone_code": "FK to volume_forecast_dim_zones.",
            "segment_code": "FK to volume_forecast_dim_segments.",
            "p10_mw": "10th percentile demand (band widens with lead time).",
            "p50_mw": "Median demand (squaring reference).",
            "p90_mw": "90th percentile demand (band widens with lead time).",
            "prev_p50_mw": "Prior-run P50 for this interval (null on the prev-run row itself).",
            "forecast_delta_mw": "p50_mw - prev_p50_mw (forecast move since last run; null on prev-run row).",
            "temperature_c": "Driver temperature from volume_forecast_bronze_weather_obs.",
            "actual_mw": "Realised demand on settled intervals (profile x full weather response); null in the future.",
            "dq_status": "Carried from meter profile (GOOD/IMPUTED/SUSPECT).",
        },
    },
    "volume_forecast_gold_consumption_st_summary": {
        "table": "Gold: short-term consumption headline KPIs (latest forecast vintage). Grain: delivery_date x zone_code x snapshot_ts.",
        "columns": {
            "delivery_date": "Day.",
            "zone_code": "FK to volume_forecast_dim_zones.",
            "snapshot_ts": "As last updated.",
            "headline": "Desk-facing summary message.",
            "avg_demand_mw": "Mean instantaneous P50 demand across the day (MW).",
            "total_demand_mwh": "Daily energy at P50 = sum(p50_mw) x 0.25h (MWh).",
            "peak_mw": "Peak interval demand.",
            "peak_interval": "When the peak occurs.",
            "band_width_mw": "Mean p90 - p10 (uncertainty).",
            "dq_status": "Worst dq_status feeding the day.",
        },
    },

    # ================================================================== #
    # 02 Customer Consumption — Long Term
    # ================================================================== #
    "volume_forecast_bronze_macro_drivers": {
        "table": "Bronze: forward structural drivers for long-term demand. Grain: vintage_id x forecast_year x zone_code.",
        "columns": {
            "ingestion_ts": "Landing time.",
            "vintage_id": "Forecast vintage (MLflow run surrogate).",
            "forecast_year": "Target calendar year.",
            "zone_code": "FK to volume_forecast_dim_zones.",
            "scenario": "BASE, HIGH_ELECTRIFICATION, or LOW_GROWTH.",
            "gdp_growth_pct": "Assumed GDP growth.",
            "ev_penetration_pct": "Share of vehicles electrified.",
            "heatpump_penetration_pct": "Share of heating electrified.",
            "efficiency_trend_pct": "Annual efficiency improvement.",
        },
    },
    "volume_forecast_silver_consumption_lt": {
        "table": "Silver: probabilistic structural demand. Grain: vintage_id x scenario x zone_code x forecast_month.",
        "columns": {
            "vintage_id": "Forecast vintage.",
            "scenario": "Scenario label.",
            "zone_code": "FK to volume_forecast_dim_zones.",
            "forecast_year": "Target year.",
            "forecast_month": "Month 1-12.",
            "season": "WINTER/SPRING/SUMMER/AUTUMN.",
            "p50_mw": "Median monthly average demand.",
            "p75_mw": "75th percentile.",
            "p90_mw": "90th percentile.",
            "electrification_uplift_mw": "Demand added by EV + heat-pump vs base.",
        },
    },
    "volume_forecast_gold_consumption_lt_shape": {
        "table": "Gold: hedge-ready long-term load shape. Grain: vintage_id x scenario x zone_code x forecast_year x season.",
        "columns": {
            "vintage_id": "Forecast vintage.",
            "scenario": "Scenario label.",
            "zone_code": "FK to volume_forecast_dim_zones.",
            "forecast_year": "Target year (Cal+1..Cal+3).",
            "season": "Season block.",
            "baseload_mw": "Average baseload volume.",
            "peakload_mw": "Average peak-window volume.",
            "p50_mw": "Median volume for hedge layering.",
            "p75_mw": "75th percentile (Cal+2 layer).",
            "p90_mw": "90th percentile (Cal+3 layer).",
            "as_of_ts": "Vintage publish time.",
        },
    },

    # ================================================================== #
    # 03 Industry Involvement
    # ================================================================== #
    "volume_forecast_dim_industrial_sites": {
        "table": "Dimension: large industrial / C&I sites (capability 03 owner). Grain: one row per site_id.",
        "columns": {
            "site_id": "Primary key, e.g. SMELT_DE_001, DATACTR_NL_001.",
            "site_name": "Site label.",
            "industry": "ALUMINIUM, CHEMICALS, DATA_CENTRE, COLD_STORE, or STEEL.",
            "zone_code": "FK to volume_forecast_dim_zones.",
            "contracted_mw": "Contracted peak demand.",
            "driver_type": "PRODUCTION_SCHEDULE, CONTINUOUS, or WEATHER.",
            "is_flexible": "True if the site participates in demand-side flexibility.",
        },
    },
    "volume_forecast_bronze_site_telemetry": {
        "table": "Bronze: industrial site metered demand. Grain: telemetry_ts x site_id.",
        "columns": {
            "ingestion_ts": "Landing time.",
            "telemetry_ts": "Measurement time.",
            "site_id": "FK to volume_forecast_dim_industrial_sites.",
            "actual_mw": "Metered demand.",
            "status": "RUNNING, REDUCED, or MAINTENANCE.",
        },
    },
    "volume_forecast_bronze_production_schedule": {
        "table": "Bronze: planned production driving industrial demand. Grain: delivery_date x site_id x shift.",
        "columns": {
            "ingestion_ts": "Landing time.",
            "delivery_date": "Day.",
            "site_id": "FK to volume_forecast_dim_industrial_sites.",
            "shift": "DAY, SWING, or NIGHT.",
            "planned_output_units": "Production volume planned.",
            "expected_mw": "Demand implied by the plan.",
        },
    },
    "volume_forecast_silver_industrial_load": {
        "table": "Silver: industrial baseline vs actual demand. Grain: interval_start x site_id.",
        "columns": {
            "delivery_date": "Day.",
            "interval_start": "Interval.",
            "site_id": "FK to volume_forecast_dim_industrial_sites.",
            "zone_code": "Denormalised zone.",
            "baseline_mw": "Expected demand (production-driven).",
            "actual_mw": "Metered demand (null for future).",
            "deviation_mw": "actual - baseline.",
        },
    },
    "volume_forecast_gold_industrial_flexibility": {
        "table": "Gold: dispatchable industrial flexibility. Grain: interval_start x site_id x flex_product. Consumed by short-term DSR desk.",
        "columns": {
            "delivery_date": "Day.",
            "interval_start": "Interval.",
            "site_id": "FK to volume_forecast_dim_industrial_sites.",
            "zone_code": "FK to volume_forecast_dim_zones.",
            "flex_product": "SHIFT, SHED, or BOOST.",
            "flexible_up_mw": "MW the site can increase (boost).",
            "flexible_down_mw": "MW the site can reduce (shed/shift).",
            "activation_price_eur_mwh": "Price to activate the flexibility.",
            "min_duration_min": "Minimum sustain duration.",
            "availability_status": "AVAILABLE, ARMED, or UNAVAILABLE.",
        },
    },

    # ================================================================== #
    # 05 Wind Forecasting
    # ================================================================== #
    "volume_forecast_dim_wind_assets": {
        "table": "Dimension: wind fleet registry (capability 05 owner). Grain: one row per asset_id.",
        "columns": {
            "asset_id": "Primary key, e.g. WIND_ON_DE_001, WIND_OFF_NL_001.",
            "asset_name": "Farm label.",
            "wind_type": "ONSHORE or OFFSHORE.",
            "zone_code": "FK to volume_forecast_dim_zones.",
            "nameplate_mw": "Rated capacity.",
            "hub_height_m": "Hub height (power-curve driver).",
            "cut_in_ms": "Cut-in wind speed.",
            "rated_ms": "Rated wind speed.",
            "cut_out_ms": "Cut-out wind speed.",
        },
    },
    "volume_forecast_bronze_nwp_wind": {
        "table": "Bronze: NWP ensemble wind forecast. Grain: forecast_ts x source x zone_code x interval_start.",
        "columns": {
            "ingestion_ts": "Landing time.",
            "forecast_ts": "NWP issue time.",
            "source": "ECMWF, GFS, or ICON (ensemble member).",
            "zone_code": "FK to volume_forecast_dim_zones.",
            "interval_start": "Target interval.",
            "wind_speed_ms": "Forecast wind speed.",
            "wind_direction_deg": "Direction 0-360.",
            "air_density_kgm3": "Air density (power yield driver).",
        },
    },
    "volume_forecast_bronze_wind_scada": {
        "table": "Bronze: wind turbine telemetry. Grain: telemetry_ts x asset_id.",
        "columns": {
            "ingestion_ts": "Landing time.",
            "telemetry_ts": "Measurement time.",
            "asset_id": "FK to volume_forecast_dim_wind_assets.",
            "actual_mw": "Metered output.",
            "wind_speed_ms": "Nacelle-measured wind speed.",
            "availability_pct": "Availability 0-100.",
            "status": "RUNNING, CURTAILED, or OUTAGE.",
        },
    },
    "volume_forecast_silver_wind_forecast": {
        "table": "Silver: probabilistic wind generation. Grain: forecast_ts x asset_id x interval_start. Feeds 07.",
        "columns": {
            "delivery_date": "Day.",
            "interval_start": "Target interval.",
            "forecast_ts": "Forecast issue time (latest = live).",
            "asset_id": "FK to volume_forecast_dim_wind_assets.",
            "zone_code": "Denormalised zone.",
            "p10_mw": "10th percentile output.",
            "p50_mw": "Median output.",
            "p90_mw": "90th percentile output.",
            "prev_p50_mw": "Prior vintage P50.",
            "forecast_delta_mw": "p50_mw - prev_p50_mw.",
            "actual_mw": "Metered output (null for future).",
        },
    },
    "volume_forecast_gold_wind_summary": {
        "table": "Gold: wind headline KPIs. Grain: delivery_date x zone_code x snapshot_ts.",
        "columns": {
            "delivery_date": "Day.",
            "zone_code": "FK to volume_forecast_dim_zones.",
            "snapshot_ts": "As last updated.",
            "headline": "Desk-facing message.",
            "total_p50_mw": "Day total at P50.",
            "peak_mw": "Peak generation interval.",
            "band_width_mw": "Mean p90 - p10.",
            "availability_pct": "Fleet availability.",
            "curtailment_risk": "LOW, MEDIUM, or HIGH.",
        },
    },

    # ================================================================== #
    # 06 Solar Forecasting
    # ================================================================== #
    "volume_forecast_dim_solar_assets": {
        "table": "Dimension: solar fleet registry (capability 06 owner). Grain: one row per asset_id.",
        "columns": {
            "asset_id": "Primary key, e.g. SOLAR_DE_001.",
            "asset_name": "Farm label.",
            "zone_code": "FK to volume_forecast_dim_zones.",
            "nameplate_mw": "Rated DC/AC capacity.",
            "tilt_deg": "Panel tilt.",
            "azimuth_deg": "Panel orientation.",
            "tracking": "FIXED, SINGLE_AXIS, or DUAL_AXIS.",
        },
    },
    "volume_forecast_bronze_nwp_solar": {
        "table": "Bronze: irradiance / cloud forecast. Grain: forecast_ts x source x zone_code x interval_start.",
        "columns": {
            "ingestion_ts": "Landing time.",
            "forecast_ts": "NWP / nowcast issue time.",
            "source": "ECMWF, SATELLITE_NOWCAST, or ICON.",
            "zone_code": "FK to volume_forecast_dim_zones.",
            "interval_start": "Target interval.",
            "ghi_wm2": "Global horizontal irradiance.",
            "cloud_cover_pct": "Cloud cover 0-100.",
            "clear_sky_ghi_wm2": "Theoretical clear-sky irradiance.",
        },
    },
    "volume_forecast_bronze_solar_scada": {
        "table": "Bronze: solar inverter telemetry. Grain: telemetry_ts x asset_id.",
        "columns": {
            "ingestion_ts": "Landing time.",
            "telemetry_ts": "Measurement time.",
            "asset_id": "FK to volume_forecast_dim_solar_assets.",
            "actual_mw": "Metered output.",
            "panel_temp_c": "Panel temperature (derate driver).",
            "availability_pct": "Availability 0-100.",
            "status": "RUNNING, CURTAILED, or OUTAGE.",
        },
    },
    "volume_forecast_silver_solar_forecast": {
        "table": "Silver: probabilistic solar generation. Grain: forecast_ts x asset_id x interval_start. Feeds 07.",
        "columns": {
            "delivery_date": "Day.",
            "interval_start": "Target interval.",
            "forecast_ts": "Forecast issue time (latest = live).",
            "asset_id": "FK to volume_forecast_dim_solar_assets.",
            "zone_code": "Denormalised zone.",
            "clear_sky_mw": "Clear-sky theoretical output.",
            "p10_mw": "10th percentile output.",
            "p50_mw": "Median output.",
            "p90_mw": "90th percentile output.",
            "prev_p50_mw": "Prior vintage P50.",
            "forecast_delta_mw": "p50_mw - prev_p50_mw.",
            "actual_mw": "Metered output (null for future).",
        },
    },
    "volume_forecast_gold_solar_summary": {
        "table": "Gold: solar headline KPIs. Grain: delivery_date x zone_code x snapshot_ts.",
        "columns": {
            "delivery_date": "Day.",
            "zone_code": "FK to volume_forecast_dim_zones.",
            "snapshot_ts": "As last updated.",
            "headline": "Desk-facing message.",
            "total_p50_mw": "Day total at P50.",
            "midday_peak_mw": "Peak in the solar window.",
            "band_width_mw": "Mean p90 - p10.",
            "btm_pv_mw": "BTM PV already netted in 04 (reconciliation).",
            "negative_price_risk": "LOW, MEDIUM, or HIGH (midday surplus).",
        },
    },

    # ================================================================== #
    # 07 Publication & Net-Volume Reconciliation
    # ================================================================== #
    "volume_forecast_gold_net_volume": {
        "table": "Gold: the official, versioned net volume (capability 07; source of truth). Grain: delivery_date x zone_code x interval_start x publication_version.",
        "columns": {
            "delivery_date": "Day.",
            "interval_start": "Interval.",
            "zone_code": "FK to volume_forecast_dim_zones.",
            "publication_version": "Monotonic version per interval.",
            "consumption_st_mw": "Short-term demand leg (01).",
            "industrial_mw": "Industrial baseline leg (03).",
            "total_demand_mw": "Sum of demand legs.",
            "wind_mw": "Wind supply leg (05).",
            "solar_mw": "Utility-scale solar leg (06).",
            "btm_pv_mw": "BTM PV (already netted in demand via 04).",
            "total_supply_mw": "Sum of supply legs (no BTM double-count).",
            "net_volume_mw": "total_demand_mw - total_supply_mw (signed).",
            "prev_published_mw": "Prior PUBLISHED net volume.",
            "revision_mw": "net_volume_mw - prev_published_mw.",
            "publication_status": "DRAFT, PUBLISHED, or SUPERSEDED.",
            "as_of_ts": "When this version was cut.",
        },
    },
    "volume_forecast_gold_publication_log": {
        "table": "Gold: publication lifecycle / SLA. Grain: delivery_date x zone_code x publication_version.",
        "columns": {
            "delivery_date": "Day.",
            "zone_code": "FK to volume_forecast_dim_zones.",
            "publication_version": "Version published.",
            "published_ts": "Publish time.",
            "legs_present": "Count of input legs available (target 5).",
            "completeness_pct": "Interval completeness of the cut.",
            "gate_status": "DRAFT, PUBLISHED, or BLOCKED.",
            "superseded_version": "Version this one replaced (null for first).",
            "note": "Reason / context for the cut.",
        },
    },
    "volume_forecast_gold_consumer_handoff": {
        "table": "Gold: consumer contract for the published net volume. Grain: one row per downstream consumer x zone.",
        "columns": {
            "consumer": "SHORT_TERM_SQUARING, LONG_TERM_CURVE, DSR_BIDSTACK, RISK, or REPORTING.",
            "zone_code": "FK to volume_forecast_dim_zones.",
            "handoff_field": "Field consumed (e.g. net_volume_mw).",
            "cadence": "INTRADAY, DAILY, or SEASONAL.",
            "latest_version": "Version the consumer last read.",
            "sla_minutes": "Freshness SLA in minutes.",
        },
    },

    # ================================================================== #
    # 08 Forecast Accuracy & Value
    # ================================================================== #
    "volume_forecast_gold_accuracy_daily": {
        "table": "Gold: daily forecast error metrics. Grain: delivery_date x leg x zone_code x lead_bucket.",
        "columns": {
            "delivery_date": "Day scored.",
            "leg": "NET, CONSUMPTION, INDUSTRIAL, WIND, or SOLAR.",
            "zone_code": "FK to volume_forecast_dim_zones.",
            "lead_bucket": "DA, H+4, H+1, or RT.",
            "forecast_mw": "Mean forecast (P50).",
            "actual_mw": "Mean realised.",
            "mae_mw": "Mean absolute error.",
            "rmse_mw": "Root mean square error.",
            "bias_mw": "Signed mean error (over/under).",
            "mape_pct": "Mean absolute percentage error.",
            "pinball_p90": "Pinball loss at P90 (band calibration).",
        },
    },
    "volume_forecast_gold_model_comparison": {
        "table": "Gold: champion / challenger comparison. Grain: model_id x leg.",
        "columns": {
            "model_id": "MLflow model / run surrogate.",
            "leg": "Forecast leg scored.",
            "role": "CHAMPION or CHALLENGER.",
            "eval_start_date": "First scored day.",
            "eval_end_date": "Last scored day.",
            "mae_mw": "MAE over the window.",
            "rmse_mw": "RMSE over the window.",
            "skill_score": "Improvement vs naive persistence baseline.",
            "is_promotion_candidate": "Challenger beats champion on the metric.",
        },
    },
    "volume_forecast_gold_cost_of_error": {
        "table": "Gold: forecast error translated to cash-out euros. Grain: delivery_date x zone_code x lead_bucket.",
        "columns": {
            "delivery_date": "Day.",
            "zone_code": "FK to volume_forecast_dim_zones.",
            "lead_bucket": "Lead-time bucket.",
            "net_error_mw": "Net volume error (signed).",
            "imbalance_price_eur_mwh": "Illustrative cash-out price.",
            "cashout_eur": "net_error_mw * imbalance_price (signed cost).",
            "avoidable_eur": "Cost attributable to model error vs irreducible.",
            "value_at_1pct_mae_eur": "Euro value of a 1% MAE improvement.",
        },
    },
    "volume_forecast_gold_drift_alerts": {
        "table": "Gold: forecast-error drift monitoring. Grain: leg x zone_code x detected_date.",
        "columns": {
            "detected_date": "When drift was flagged.",
            "leg": "Forecast leg.",
            "zone_code": "FK to volume_forecast_dim_zones.",
            "metric": "MAE, BIAS, or BAND_CALIBRATION.",
            "baseline_value": "Reference (training / trailing window).",
            "current_value": "Current value.",
            "drift_pct": "Relative change.",
            "drift_status": "STABLE, WATCH, or DRIFT.",
        },
    },
}
# fmt: on


# Per-notebook table bundles ------------------------------------------------ #
_NOTEBOOK_04 = (
    "volume_forecast_dim_zones",
    "volume_forecast_dim_segments",
    "volume_forecast_dim_intervals",
    "volume_forecast_bronze_meter_reads",
    "volume_forecast_bronze_meter_events",
    "volume_forecast_silver_btm_pv",
    "volume_forecast_silver_meter_profile",
    "volume_forecast_gold_metering_quality",
)

_NOTEBOOK_01 = (
    "volume_forecast_bronze_weather_obs",
    "volume_forecast_silver_consumption_st",
    "volume_forecast_gold_consumption_st_summary",
)

_NOTEBOOK_02 = (
    "volume_forecast_bronze_macro_drivers",
    "volume_forecast_silver_consumption_lt",
    "volume_forecast_gold_consumption_lt_shape",
)

_NOTEBOOK_03 = (
    "volume_forecast_dim_industrial_sites",
    "volume_forecast_bronze_site_telemetry",
    "volume_forecast_bronze_production_schedule",
    "volume_forecast_silver_industrial_load",
    "volume_forecast_gold_industrial_flexibility",
)

_NOTEBOOK_05 = (
    "volume_forecast_dim_wind_assets",
    "volume_forecast_bronze_nwp_wind",
    "volume_forecast_bronze_wind_scada",
    "volume_forecast_silver_wind_forecast",
    "volume_forecast_gold_wind_summary",
)

_NOTEBOOK_06 = (
    "volume_forecast_dim_solar_assets",
    "volume_forecast_bronze_nwp_solar",
    "volume_forecast_bronze_solar_scada",
    "volume_forecast_silver_solar_forecast",
    "volume_forecast_gold_solar_summary",
)

_NOTEBOOK_07 = (
    "volume_forecast_gold_net_volume",
    "volume_forecast_gold_publication_log",
    "volume_forecast_gold_consumer_handoff",
)

_NOTEBOOK_08 = (
    "volume_forecast_gold_accuracy_daily",
    "volume_forecast_gold_model_comparison",
    "volume_forecast_gold_cost_of_error",
    "volume_forecast_gold_drift_alerts",
)


def apply_volume_forecast_notebook_04_comments(spark: Any, catalog: str, schema: str) -> None:
    _apply_bundle(spark, catalog, schema, _NOTEBOOK_04)


def apply_volume_forecast_notebook_01_comments(spark: Any, catalog: str, schema: str) -> None:
    _apply_bundle(spark, catalog, schema, _NOTEBOOK_01)


def apply_volume_forecast_notebook_02_comments(spark: Any, catalog: str, schema: str) -> None:
    _apply_bundle(spark, catalog, schema, _NOTEBOOK_02)


def apply_volume_forecast_notebook_03_comments(spark: Any, catalog: str, schema: str) -> None:
    _apply_bundle(spark, catalog, schema, _NOTEBOOK_03)


def apply_volume_forecast_notebook_05_comments(spark: Any, catalog: str, schema: str) -> None:
    _apply_bundle(spark, catalog, schema, _NOTEBOOK_05)


def apply_volume_forecast_notebook_06_comments(spark: Any, catalog: str, schema: str) -> None:
    _apply_bundle(spark, catalog, schema, _NOTEBOOK_06)


def apply_volume_forecast_notebook_07_comments(spark: Any, catalog: str, schema: str) -> None:
    _apply_bundle(spark, catalog, schema, _NOTEBOOK_07)


def apply_volume_forecast_notebook_08_comments(spark: Any, catalog: str, schema: str) -> None:
    _apply_bundle(spark, catalog, schema, _NOTEBOOK_08)


def apply_all_volume_forecast_comments(spark: Any, catalog: str, schema: str) -> None:
    """Apply every bundle, skipping tables not yet materialised."""
    _apply_bundle(spark, catalog, schema, tuple(TABLE_METADATA.keys()), skip_missing=True)
