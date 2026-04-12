"""
European wholesale-style *simulated* demo datasets.

These rows are **synthetic** and **not** copied from ENTSO-E, EPEX, ECMWF, EEX, or any vendor.
They are shaped like typical public or licensed feeds (column names, units, cadence) so that
notebooks and pipelines can be exercised against realistic schemas.

See `features/01-*.md` … `04-*.md` for the capability specs this data supports.
"""

from __future__ import annotations

import datetime as dt
import math
import random
import sys
from pathlib import Path
from typing import Any, List, Tuple

_dd = Path(__file__).resolve().parent
if str(_dd) not in sys.path:
    sys.path.insert(0, str(_dd))

from synthetic_generators import (
    DEMO_START,
    HOURS_MAIN,
    _da_price_de_lu_eur_mwh,
    _doy,
    _fr_spread_vs_de,
    _nl_spread_vs_de,
    _rng,
    _hour_series,
)

# ---------------------------------------------------------------------------
# Documentation: what each *family* of table is *inspired by* (still synthetic)
# ---------------------------------------------------------------------------
SIMULATED_SOURCE_FAMILIES = {
    "epex_spot_style": "Day-ahead / intraday power — schema style similar to exchange hourly results (synthetic).",
    "entsoe_transparency_style": "TSO / transparency — load and generation actuals (synthetic, not ENTSO-E data).",
    "german_tso_imbalance_style": "German control-area imbalance settlement — quarter-hourly cadence possible (synthetic).",
    "nwp_ecmwf_style": "Numerical weather — run time / valid time / gridded scalars (synthetic, not ECMWF).",
    "eex_gas_futures_style": "Gas hub forward / spot assessments (synthetic).",
    "eu_ets_style": "EU ETS allowance daily prices (synthetic).",
    "broker_assessment_style": "End-of-day broker curve assessment (synthetic).",
    "otc_trade_capture_style": "OTC deal capture fields aligned with REMIT/EMIR *shape* (synthetic deals).",
}


def demo_rng() -> random.Random:
    return _rng()


# ---------------------------------------------------------------------------
# 01 — Market data: bronze-style prices (lineage + licence note)
# ---------------------------------------------------------------------------
def bronze_prices_spot_rows(
    n_hours: int = HOURS_MAIN,
) -> List[Tuple[Any, ...]]:
    """
    Simulates vendor/bronze landing: ingestion timestamp, source label, delivery hour, zone, product.
    Inspired by: exchange DA/ID results + metadata for SDAC/SIDC-style workflows.
    """
    r = demo_rng()
    rows: List[Tuple[Any, ...]] = []
    for ts in _hour_series(n_hours):
        ingestion = ts + dt.timedelta(minutes=38 + r.randint(0, 40))  # delayed publication
        de = round(_da_price_de_lu_eur_mwh(ts, r), 2)
        nl = round(de + _nl_spread_vs_de(de, ts, r), 2)
        fr = round(de + _fr_spread_vs_de(de, r), 2)
        for zone, px, prod, src in [
            ("DE-LU", de, "DA_HOUR", "EPEX_SPOT_SIM"),
            ("NL", nl, "DA_HOUR", "EPEX_SPOT_SIM"),
            ("FR", fr, "DA_HOUR", "EPEX_SPOT_SIM"),
        ]:
            rows.append(
                (
                    ingestion,
                    src,
                    "public_exchange_results_simulated",
                    ts,
                    zone,
                    prod,
                    float(px),
                    "EUR/MWh",
                    "SYNTHETIC_DEMO_ONLY",
                )
            )
        id_px = round(de + r.gauss(1.1, 6.2), 2)
        rows.append(
            (
                ingestion + dt.timedelta(minutes=12),
                "EPEX_SPOT_SIM",
                "continuous_intraday_index_simulated",
                ts,
                "DE-LU",
                "ID_15M_INDEX",
                max(-200.0, min(450.0, id_px)),
                "EUR/MWh",
                "SYNTHETIC_DEMO_ONLY",
            )
        )
    return rows


BRONZE_PRICES_SPOT_COLUMNS = (
    "ingestion_ts",
    "source_system",
    "dataset_family",
    "delivery_start_ts",
    "bidding_zone_eic",
    "product_code",
    "value",
    "unit",
    "data_license_note",
)


# ---------------------------------------------------------------------------
# 01 — ENTSO-E *style* actual generation / load (synthetic)
# ---------------------------------------------------------------------------
def entsoe_transparency_style_rows(n_hours: int = 72 * 24) -> List[Tuple[Any, ...]]:
    """Hourly-ish actuals for DE-LU: load and renewable aggregates (synthetic)."""
    r = demo_rng()
    rows: List[Tuple[Any, ...]] = []
    for ts in _hour_series(min(n_hours, HOURS_MAIN)):
        hod, dow, doy = ts.hour, ts.weekday(), _doy(ts)
        load = (
            51_500.0
            + 8_200.0 * math.exp(-((hod - 8.5) ** 2) / 14.0)
            + 6_800.0 * math.exp(-((hod - 19.0) ** 2) / 15.0)
            + (2_100.0 if dow < 5 else -4_200.0)
            + 5.0 * math.sin(doy / 365.25 * 2 * math.pi)
            + r.gauss(0, 600.0)
        )
        wind = max(500.0, 16_000.0 + 10_000.0 * math.sin((doy + hod) / 25.0) + r.gauss(0, 900.0))
        solar = max(0.0, 28_000.0 * math.exp(-((hod - 13.0) ** 2) / 22.0) + r.gauss(0, 1_100.0))
        rows.append(
            (
                ts,
                "10Y1001A1001A82H",
                "Actual Total Load",
                round(load, 1),
                "MW",
                "ENTSOE_TP_STYLE_SIM",
            )
        )
        rows.append(
            (
                ts,
                "10Y1001A1001A82H",
                "Actual Generation Wind Onshore",
                round(wind * 0.72, 1),
                "MW",
                "ENTSOE_TP_STYLE_SIM",
            )
        )
        rows.append(
            (
                ts,
                "10Y1001A1001A82H",
                "Actual Generation Solar",
                round(solar, 1),
                "MW",
                "ENTSOE_TP_STYLE_SIM",
            )
        )
    return rows


ENTSOE_STYLE_COLUMNS = (
    "timestamp_utc",
    "eic_bidding_zone",
    "series_name",
    "value",
    "unit",
    "source_note",
)


# ---------------------------------------------------------------------------
# 01 — German imbalance prices (15-minute product simulation, hourly sample)
# ---------------------------------------------------------------------------
def german_imbalance_prices_style_rows(n_hours: int = HOURS_MAIN) -> List[Tuple[Any, ...]]:
    """Single price index per hour for long/short imbalance (synthetic)."""
    r = demo_rng()
    rows: List[Tuple[Any, ...]] = []
    for ts in _hour_series(n_hours):
        de = _da_price_de_lu_eur_mwh(ts, r)
        imb_long = de + r.gauss(4.5, 9.0)
        imb_short = de - r.gauss(2.0, 7.0)
        for tso in ("50Hertz", "Amprion", "TenneT", "TransnetBW"):
            rows.append(
                (
                    ts,
                    tso,
                    "imbalance_long_eur_mwh",
                    round(max(-500.0, min(500.0, imb_long + r.gauss(0, 2))), 2),
                    15,
                    "REGELENERGIE_STYLE_SIM",
                )
            )
            rows.append(
                (
                    ts,
                    tso,
                    "imbalance_short_eur_mwh",
                    round(max(-500.0, min(500.0, imb_short + r.gauss(0, 2))), 2),
                    15,
                    "REGELENERGIE_STYLE_SIM",
                )
            )
    return rows


GERMAN_IMBALANCE_COLUMNS = (
    "timestamp_utc",
    "control_area_label",
    "price_type",
    "eur_per_mwh",
    "period_minutes",
    "source_note",
)


# ---------------------------------------------------------------------------
# 01 — NWP-style surface point (synthetic ECMWF-like run metadata)
# ---------------------------------------------------------------------------
def nwp_ecmwf_style_rows(n_hours: int = 168) -> List[Tuple[Any, ...]]:
    """Point forecast near Frankfurt-ish coordinates — not real NWP output."""
    r = demo_rng()
    lat, lon = 50.11, 8.68
    rows: List[Tuple[Any, ...]] = []
    base_run = DEMO_START.replace(hour=0, minute=0, second=0)
    for h in range(min(n_hours, 168)):
        valid = DEMO_START + dt.timedelta(hours=h)
        run = base_run + dt.timedelta(hours=(h // 24) * 24)  # 00Z cycles
        hod, doy = valid.hour, _doy(valid)
        t2m = 5.0 + 10.0 * math.sin((doy - 80) / 365.25 * 2 * math.pi) + 2.0 * math.sin(hod / 24 * math.pi)
        t2m += r.gauss(0, 1.0)
        w100 = max(0.5, 7.0 + 3.5 * math.sin((doy + hod) / 30.0) + r.gauss(0, 1.2))
        ssrd = max(0.0, 450.0 * math.exp(-((hod - 13.0) ** 2) / 20.0))
        rows.append(
            (
                run,
                valid,
                lat,
                lon,
                "DE-LU",
                round(t2m, 2),
                round(w100, 2),
                round(ssrd, 1),
                "IFS_STYLE_SIM_HRES",
            )
        )
    return rows


NWP_ECMWF_STYLE_COLUMNS = (
    "model_run_ts_utc",
    "valid_ts_utc",
    "lat",
    "lon",
    "zone_label",
    "t2m_celsius",
    "wind100_ms",
    "ssrd_wm2",
    "model_id_simulated",
)


# ---------------------------------------------------------------------------
# 01 — Gas hub (TTF-style) day-ahead assessment
# ---------------------------------------------------------------------------
def gas_hub_ttf_style_rows(n_days: int = 90) -> List[Tuple[Any, ...]]:
    r = demo_rng()
    rows: List[Tuple[Any, ...]] = []
    for i in range(n_days):
        d = (DEMO_START + dt.timedelta(days=i)).date()
        ttf = 32.0 + 7.5 * math.sin((i + 35) / 365.25 * math.pi) + r.gauss(0, 1.4)
        rows.append(
            (
                d,
                "TTF",
                "DA_GAS_SIM",
                round(max(8.0, ttf), 2),
                "EUR/MWh",
                "EEX_GAS_OR_BROKER_STYLE_SIM",
            )
        )
    return rows


GAS_TTF_STYLE_COLUMNS = (
    "gas_day_date",
    "hub_id",
    "product_code",
    "price",
    "unit",
    "source_note",
)


# ---------------------------------------------------------------------------
# 01 — EU ETS (daily)
# ---------------------------------------------------------------------------
def eua_ets_daily_rows(n_days: int = 90) -> List[Tuple[Any, ...]]:
    r = demo_rng()
    rows: List[Tuple[Any, ...]] = []
    for i in range(n_days):
        d = (DEMO_START + dt.timedelta(days=i)).date()
        eua = 68.0 + 11.0 * math.sin((i + 18) / 365.25 * 2 * math.pi) + r.gauss(0, 2.0)
        rows.append((d, "EUA_DEC24_SIM", round(max(15.0, eua), 2), "EUR/tCO2", "EEX_ETS_STYLE_SIM"))
    return rows


EUA_ETS_COLUMNS = ("business_date", "contract_id_sim", "settle_eur_tco2", "unit", "source_note")


# ---------------------------------------------------------------------------
# 02 — OTC trades (synthetic REMIT-shaped fields)
# ---------------------------------------------------------------------------
def otc_trades_remit_style_rows(n: int = 120) -> List[Tuple[Any, ...]]:
    r = demo_rng()
    cp_leis = [
        "5299009YR0QU2N6HX37",
        "529900C0OSE0GZ9W2Y29",
        "984500F5BD5BE6497C41",
    ]
    rows: List[Tuple[Any, ...]] = []
    for i in range(n):
        ts = DEMO_START + dt.timedelta(hours=8 + (i * 17) % (80 * 24))
        zone = r.choice(["DE-LU", "NL", "FR"])
        mw = round(5.0 + r.random() * 45.0, 1)
        px = round(65.0 + r.gauss(0, 12.0), 2)
        rows.append(
            (
                f"OTC-DEMO-{202410000 + i}",
                ts,
                zone,
                "FWD_SWAP_HR",
                mw,
                "fixed",
                px,
                r.choice(cp_leis),
                r.choice(["bilateral", "cleared"]),
                True,
                "SYNTHETIC_TRADE_CAPTURE_DEMO",
            )
        )
    return rows


OTC_TRADES_COLUMNS = (
    "trade_id",
    "execution_ts_utc",
    "bidding_zone",
    "product_type",
    "volume_mw",
    "price_type",
    "fixed_price_eur_mwh",
    "counterparty_lei_simulated",
    "clearing_mode",
    "remit_reportable_flag",
    "source_note",
)


# ---------------------------------------------------------------------------
# 04 — Strategy: simple strategy definitions + backtest summary (synthetic)
# ---------------------------------------------------------------------------
def strategy_definitions_demo_rows() -> List[Tuple[Any, ...]]:
    return [
        (
            "strat-id-meanrev-01",
            "Mean reversion on DA vs ID spread (DE-LU)",
            "active",
            "paper",
            "2024-10-01",
            "SYNTHETIC",
        ),
        (
            "strat-imb-hedge-02",
            "Imbalance exposure hedge using TSO signals",
            "pilot",
            "shadow",
            "2024-10-15",
            "SYNTHETIC",
        ),
    ]


STRATEGY_DEF_COLUMNS = (
    "strategy_id",
    "description",
    "status",
    "deployment_mode",
    "created_date",
    "source_note",
)


def backtest_summary_demo_rows() -> List[Tuple[Any, ...]]:
    r = demo_rng()
    return [
        (
            "strat-id-meanrev-01",
            "bt-2024w41",
            round(r.gauss(1200.0, 400.0), 1),
            round(r.gauss(1.1, 0.3), 2),
            round(r.gauss(-800.0, 200.0), 1),
            "EUR_SIM",
        ),
        (
            "strat-imb-hedge-02",
            "bt-2024w41",
            round(r.gauss(400.0, 150.0), 1),
            round(r.gauss(0.85, 0.25), 2),
            round(r.gauss(-350.0, 100.0), 1),
            "EUR_SIM",
        ),
    ]


BACKTEST_SUMMARY_COLUMNS = (
    "strategy_id",
    "backtest_run_id",
    "net_pnl_eur_sim",
    "sharpe_ratio_sim",
    "max_drawdown_eur_sim",
    "currency",
)
