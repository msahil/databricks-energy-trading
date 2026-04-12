#!/usr/bin/env python3
"""Generate .ipynb demo notebooks from embedded templates (run from repo; not required at runtime)."""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEMO_DATA = HERE.parent / "demo_data"


def _nb(cells: list[tuple[str, str]]) -> dict:
    out_cells = []
    for kind, text in cells:
        src = text if text.endswith("\n") else text + "\n"
        if kind == "md":
            out_cells.append({"cell_type": "markdown", "metadata": {}, "source": src.splitlines(keepends=True)})
        else:
            out_cells.append({"cell_type": "code", "metadata": {}, "source": src.splitlines(keepends=True), "outputs": []})
    return {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "pygments_lexer": "ipython3"},
        },
        "cells": out_cells,
    }


PATH_SETUP = r"""
import os
import sys
from pathlib import Path

# Uploaded demo modules (Databricks). `dbfs:/tmp/...` is readable on shared UC clusters; FileStore path is a fallback.
sys.path.insert(0, "/dbfs/tmp/energy-trading-forecast-demo")
sys.path.insert(0, "/dbfs/FileStore/energy-trading-forecasting-demo/demo_data")
_env = os.environ.get("DEMO_DATA_PATH", "").strip()
if _env:
    sys.path.insert(0, _env)

CWD = Path.cwd()
for dd in (
    CWD / "modules" / "forecasting" / "demo_data",
    CWD / "demo_data",
    CWD.parent / "demo_data",
):
    if (dd / "notebook_helpers.py").is_file():
        sys.path.insert(0, str(dd))
        break

import notebook_helpers as nh
nh.ensure_demo_data_on_path()
# Matches modules/forecasting/README.md → unity_catalog.schemas (override with DEMO_UC_* env)
print(
    "Unity Catalog Delta target:",
    nh.catalog_schema(),
    "— example:",
    nh.full_table_name("demo_prices_spot_hourly"),
)
""".strip()


NB01 = [
    (
        "md",
        """# 01 — Market data & visualisation (demo)

**Synthetic data only.** Tables are shaped like public or licensed European wholesale feeds (EPEX-style results, ENTSO-E Transparency–style actuals, NWP-style weather, TTF-style gas, EU ETS–style CO₂) but **are not** real vendor or exchange data.

See `modules/forecasting/features/01-market-data-and-visualisation.md`.""",
    ),
    (
        "code",
        PATH_SETUP
        + """

import synthetic_generators as sg
import european_demo_sources as eds

spark = nh.get_spark()
cat, sch = nh.catalog_schema()
print(f"Target catalog: {cat}.{sch} | Spark session: {spark is not None}")
print("Source families:", list(eds.SIMULATED_SOURCE_FAMILIES.keys()))
""",
    ),
    (
        "code",
        """
# Reference data & prices (hourly, ~90d)
nh.write_demo_table(
    "demo_reference_bidding_zones",
    sg.bidding_zones_rows(),
    ("zone_code", "name", "country", "eic_bidding_zone"),
    spark=spark,
)
nh.write_demo_table(
    "demo_prices_spot_hourly",
    sg.prices_spot_rows(),
    ("delivery_ts", "bidding_zone", "product_code", "venue", "price_eur_mwh", "unit"),
    spark=spark,
)
nh.write_demo_table(
    "demo_bronze_prices_spot",
    eds.bronze_prices_spot_rows(),
    eds.BRONZE_PRICES_SPOT_COLUMNS,
    spark=spark,
)
nh.write_demo_table(
    "demo_entsoe_transparency_style",
    eds.entsoe_transparency_style_rows(72 * 24),
    eds.ENTSOE_STYLE_COLUMNS,
    spark=spark,
)
nh.write_demo_table(
    "demo_german_imbalance_prices_style",
    eds.german_imbalance_prices_style_rows(168),
    eds.GERMAN_IMBALANCE_COLUMNS,
    spark=spark,
)
nh.write_demo_table(
    "demo_nwp_ecmwf_surface_style",
    eds.nwp_ecmwf_style_rows(168),
    eds.NWP_ECMWF_STYLE_COLUMNS,
    spark=spark,
)
nh.write_demo_table(
    "demo_gas_hub_ttf_style",
    eds.gas_hub_ttf_style_rows(90),
    eds.GAS_TTF_STYLE_COLUMNS,
    spark=spark,
)
nh.write_demo_table(
    "demo_eua_ets_daily_style",
    eds.eua_ets_daily_rows(90),
    eds.EUA_ETS_COLUMNS,
    spark=spark,
)
nh.write_demo_table(
    "demo_grid_signals",
    sg.grid_signals_rows(),
    ("ts", "tso", "metric", "unit", "value"),
    spark=spark,
)
nh.write_demo_table(
    "demo_fundamentals_de_lu",
    sg.fundamentals_rows(),
    ("ts", "zone", "temp_c", "wind_ms", "solar_mw_est", "load_mw", "residual_mw"),
    spark=spark,
)
nh.write_demo_table(
    "demo_cross_border_flows",
    sg.cross_border_flows_rows(),
    ("ts", "from_country", "to_country", "direction", "mw"),
    spark=spark,
)
print("Market data demo tables written.")
""",
    ),
]

NB02 = [
    (
        "md",
        """# 02 — Trade capture & pricing (demo)

Synthetic OTC-style deals with REMIT-shaped fields (LEI, clearing mode). **Not** real trades.

See `features/02-trade-capture-and-pricing.md`.""",
    ),
    (
        "code",
        PATH_SETUP
        + """

import european_demo_sources as eds
import synthetic_generators as sg

spark = nh.get_spark()
""",
    ),
    (
        "code",
        """
nh.write_demo_table(
    "demo_trades_otc_remit_style",
    eds.otc_trades_remit_style_rows(120),
    eds.OTC_TRADES_COLUMNS,
    spark=spark,
)
# Supporting reference + downstream registry (catalogue style)
nh.write_demo_table(
    "demo_consumer_contracts",
    sg.consumer_contracts_rows(),
    ("consumer_id", "contract_version", "status", "notes"),
    spark=spark,
)
nh.write_demo_table(
    "demo_downstream_exports",
    sg.downstream_export_rows(),
    ("export_id", "consumer", "forecast_scope_id", "exported_at", "status", "table_ref", "schema_version"),
    spark=spark,
)
print("Trade capture demo tables written.")
""",
    ),
]

NB03 = [
    (
        "md",
        """# 03 — Forecasting & predictive analytics (demo)

Model outputs, backtest grids, drift — **synthetic** metrics for pipeline testing.

See `features/03-forecasting-and-predictive-analytics.md`.""",
    ),
    (
        "code",
        PATH_SETUP
        + """

import synthetic_generators as sg

spark = nh.get_spark()
""",
    ),
    (
        "code",
        """
nh.write_demo_table(
    "demo_forecasts_load_gen",
    sg.forecasts_load_gen_rows(),
    ("ts", "zone", "model_id", "load_fcast_mw", "wind_fcast_mw", "solar_fcast_mw", "residual_mw"),
    spark=spark,
)
nh.write_demo_table(
    "demo_forecasts_market_prices",
    sg.forecasts_market_prices_rows(),
    ("ts", "zone", "product", "mid_eur_mwh", "q10_eur_mwh", "q90_eur_mwh", "imbalance_risk_index"),
    spark=spark,
)
nh.write_demo_table(
    "demo_carbon_spark_daily",
    sg.carbon_spark_rows(),
    ("ts", "zone", "eua_eur_t", "goo_eur_mwh", "ttf_eur_mwh", "clean_spark_proxy"),
    spark=spark,
)
nh.write_demo_table(
    "demo_backtest_metrics",
    sg.backtest_metrics_rows(),
    ("run_id", "model_id", "product", "zone", "horizon", "mae", "rmse", "mape", "skill", "pinball"),
    spark=spark,
)
nh.write_demo_table(
    "demo_drift_metrics",
    sg.drift_metrics_rows(),
    ("as_of_date", "model_id", "feature_group", "zone", "psi"),
    spark=spark,
)
nh.write_demo_table(
    "demo_regime_labels",
    sg.regime_labels_rows(),
    ("regime_id", "driver", "effect", "month_tag"),
    spark=spark,
)
print("Forecasting demo tables written.")
""",
    ),
]

NB04 = [
    (
        "md",
        """# 04 — Strategy, optimisation & algo (demo)

Alerts, backtest summaries, scenario catalogue — synthetic operations data.

See `features/04-strategy-optimisation-and-algorithmic-trading.md`.""",
    ),
    (
        "code",
        PATH_SETUP
        + """

import european_demo_sources as eds
import synthetic_generators as sg

spark = nh.get_spark()
""",
    ),
    (
        "code",
        """
nh.write_demo_table(
    "demo_strategy_definitions",
    eds.strategy_definitions_demo_rows(),
    eds.STRATEGY_DEF_COLUMNS,
    spark=spark,
)
nh.write_demo_table(
    "demo_backtest_summary",
    eds.backtest_summary_demo_rows(),
    eds.BACKTEST_SUMMARY_COLUMNS,
    spark=spark,
)
nh.write_demo_table(
    "demo_alert_rules",
    sg.alert_rules_rows(),
    ("rule_id", "series", "comparator", "threshold", "zone", "unit", "status"),
    spark=spark,
)
nh.write_demo_table(
    "demo_alert_events",
    sg.alert_events_rows(),
    ("event_id", "event_ts", "rule_id", "severity", "message"),
    spark=spark,
)
nh.write_demo_table(
    "demo_dashboard_kpis",
    sg.dashboard_kpis_rows(),
    ("month", "kpi", "zone", "value", "unit"),
    spark=spark,
)
nh.write_demo_table(
    "demo_tso_market_events",
    sg.tso_market_events_rows(),
    ("event_ts", "source", "category", "description"),
    spark=spark,
)
nh.write_demo_table(
    "demo_viz_series_long",
    sg.viz_series_long_rows(),
    ("ts", "zone", "series", "unit", "value"),
    spark=spark,
)
nh.write_demo_table(
    "demo_forecast_vs_actual",
    sg.forecast_vs_actual_rows(),
    ("ts", "zone", "product", "forecast_eur_mwh", "actual_eur_mwh", "error_eur_mwh", "ensemble_spread"),
    spark=spark,
)
nh.write_demo_table(
    "demo_forecast_scope_catalog",
    sg.forecast_scope_catalog_rows(),
    ("scope_id", "forecast_type", "use_case", "product", "zone", "status"),
    spark=spark,
)
nh.write_demo_table(
    "demo_scenario_definitions",
    sg.scenario_definitions_rows(),
    ("scenario_id", "label", "description"),
    spark=spark,
)
nh.write_demo_table(
    "demo_user_personas",
    sg.user_personas_rows(),
    ("persona_id", "role", "external_customer"),
    spark=spark,
)
print("Strategy / analytics demo tables written.")
""",
    ),
]


def main() -> None:
    HERE.mkdir(parents=True, exist_ok=True)
    (HERE / "01_market_data_and_visualisation.ipynb").write_text(json.dumps(_nb(NB01), indent=1))
    (HERE / "02_trade_capture_and_pricing.ipynb").write_text(json.dumps(_nb(NB02), indent=1))
    (HERE / "03_forecasting_and_predictive_analytics.ipynb").write_text(json.dumps(_nb(NB03), indent=1))
    (HERE / "04_strategy_optimisation_and_algo_trading.ipynb").write_text(json.dumps(_nb(NB04), indent=1))
    print("Wrote 4 notebooks to", HERE)


if __name__ == "__main__":
    main()
