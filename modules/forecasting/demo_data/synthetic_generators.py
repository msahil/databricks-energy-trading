"""
Synthetic European power-market demo data (fully fictional, no external feeds).

Deterministic (seeded) series with plausible DE-LU / neighbour dynamics: duck curves,
weekend discounts, occasional negative DA hours, correlated zones, and TSO-scale MW.

See also `european_demo_sources.py` for bronze-style lineage and ENTSO-E/NWP/TTF/EUA-shaped
demo tables used by `notebooks/01_*.ipynb`.
"""

from __future__ import annotations

import datetime as dt
import math
import random
from typing import Any, List, Tuple

RNG_SEED = 42
DEMO_START = dt.datetime(2024, 10, 1, 0, 0, 0)
HOURS_MAIN = 90 * 24


def _rng() -> random.Random:
    return random.Random(RNG_SEED)


def _hour_series(n_hours: int, start: dt.datetime = DEMO_START) -> List[dt.datetime]:
    return [start + dt.timedelta(hours=h) for h in range(n_hours)]


def _doy(ts: dt.datetime) -> int:
    return int(ts.strftime("%j"))


def _da_price_de_lu_eur_mwh(ts: dt.datetime, r: random.Random) -> float:
    hod = ts.hour
    dow = ts.weekday()
    doy = _doy(ts)
    seasonal = 14.0 * math.sin((doy - 15) / 365.25 * 2 * math.pi)
    duck = -22.0 * math.exp(-((hod - 13) ** 2) / 20.0) if 5 <= hod <= 21 else 0.0
    peaks = (
        10.5 * math.exp(-((hod - 7.5) ** 2) / 10.0)
        + 9.0 * math.exp(-((hod - 19.0) ** 2) / 12.0)
    )
    weekend = -9.0 if dow >= 5 else 0.0
    base = 74.0 + seasonal + duck + peaks + weekend
    noise = r.gauss(0.0, 5.2)
    spike = r.gauss(45.0, 12.0) if r.random() < 0.0018 else 0.0
    neg = 0.0
    if r.random() < 0.028 and dow < 5 and 9 <= hod <= 17:
        neg = -(18.0 + r.random() * 95.0)
    p = base + noise + spike + neg
    return max(-180.0, min(420.0, p))


def _nl_spread_vs_de(de_price: float, ts: dt.datetime, r: random.Random) -> float:
    dow = ts.weekday()
    basis = 1.8 + 0.6 * math.sin(_doy(ts) / 365.25 * 2 * math.pi)
    congestion = 3.2 if dow < 5 and 7 <= ts.hour <= 9 else 0.0
    noise = r.gauss(0.0, 2.1)
    return round(basis + congestion + noise + r.gauss(0, 0.15) * abs(de_price) * 0.01, 3)


def _fr_spread_vs_de(de_price: float, r: random.Random) -> float:
    return round(r.gauss(-2.4, 2.8) + 0.008 * (de_price - 75.0), 3)


def bidding_zones_rows() -> List[Tuple[Any, ...]]:
    return [
        ("DE-LU", "Germany-Luxembourg", "DE", "10Y1001A1001A82H"),
        ("NL", "Netherlands", "NL", "10YNL----------L"),
        ("FR", "France", "FR", "10YFR-RTE------C"),
        ("AT", "Austria", "AT", "10YAT-APG------L"),
        ("PL", "Poland", "PL", "10YPL-AREA-----S"),
        ("BE", "Belgium", "BE", "10YBE----------2"),
        ("DK1", "Denmark West", "DK", "10Y1001A1001A39I"),
        ("CH", "Switzerland", "CH", "10YCH-SWISSGRIDZ"),
    ]


def prices_spot_rows() -> List[Tuple[Any, ...]]:
    r = _rng()
    rows: List[Tuple[Any, ...]] = []
    for ts in _hour_series(HOURS_MAIN):
        de = round(_da_price_de_lu_eur_mwh(ts, r), 2)
        nl = round(de + _nl_spread_vs_de(de, ts, r), 2)
        fr = round(de + _fr_spread_vs_de(de, r), 2)
        for area, px in [("DE-LU", de), ("NL", nl), ("FR", fr)]:
            rows.append((ts, area, "EPEX_DA_HR", "EPEX", float(px), "EUR/MWh"))
        id_mid = de + r.gauss(1.2, 6.5)
        rows.append(
            (ts, "DE-LU", "EPEX_ID_INDEX_15M", "EPEX", round(max(-200.0, min(450.0, id_mid)), 2), "EUR/MWh")
        )
    return rows


def grid_signals_rows() -> List[Tuple[Any, ...]]:
    r = _rng()
    rows: List[Tuple[Any, ...]] = []
    tsos = ["TenneT", "Amprion", "50Hertz", "TransnetBW"]
    for ts in _hour_series(HOURS_MAIN):
        hod, dow = ts.hour, ts.weekday()
        for tso in tsos:
            afrr = 11.0 + 6.0 * math.exp(-((hod - 14) ** 2) / 50.0) + r.gauss(0, 1.2)
            if dow >= 5:
                afrr -= 1.5
            rows.append((ts, tso, "aFRR_capacity_price", "EUR/MW/h", round(max(2.0, afrr), 2)))
        redispatch = -120.0 * math.exp(-((hod - 12) ** 2) / 30.0) + r.gauss(0, 35.0)
        rows.append((ts, "Amprion", "redispatch_volume_net", "MW", round(redispatch, 1)))
        rows.append((ts, "TenneT", "redispatch_volume_net", "MW", round(redispatch * 0.92 + r.gauss(0, 20), 1)))
        w50 = 7200.0 + 2800.0 * math.sin(hod / 24.0 * math.pi) + r.gauss(0, 180.0)
        rows.append((ts, "50Hertz", "wind_onshore_actual", "MW", round(max(0.0, w50), 1)))
        rows.append(
            (ts, "TransnetBW", "solar_actual_est", "MW", round(max(0.0, 4800.0 * math.exp(-((hod - 13) ** 2) / 18.0)), 1))
        )
    return rows


def fundamentals_rows() -> List[Tuple[Any, ...]]:
    r = _rng()
    rows: List[Tuple[Any, ...]] = []
    for ts in _hour_series(HOURS_MAIN):
        doy = _doy(ts)
        hod = ts.hour
        dow = ts.weekday()
        temp = 4.5 + 11.0 * math.sin((doy - 100) / 365.25 * 2 * math.pi) + 2.5 * math.sin(hod / 24 * math.pi)
        temp += r.gauss(0, 1.1)
        wspd = max(0.5, 7.5 + 3.0 * math.sin((doy + hod) / 40.0) + r.gauss(0, 1.4))
        solar = max(0.0, 38_000.0 * math.exp(-((hod - 13.2) ** 2) / 24.0) * (0.55 + 0.45 * max(0.0, math.sin(doy / 365 * math.pi))))
        solar += r.gauss(0, 900.0)
        load = (
            52_000.0
            + 9_200.0 * (0.35 * math.exp(-((hod - 8.5) ** 2) / 12.0) + 0.4 * math.exp(-((hod - 19.0) ** 2) / 14.0))
            + (2_400.0 if dow < 5 else -4_800.0)
            + 6.0 * math.sin(doy / 365.25 * 2 * math.pi)
            + r.gauss(0, 650.0)
        )
        res = load - solar - (wspd * 950.0 + r.gauss(0, 400.0))
        rows.append(
            (ts, "DE-LU", round(temp, 2), round(wspd, 2), round(max(0.0, solar), 1), round(load, 1), round(res, 1))
        )
    return rows


def cross_border_flows_rows() -> List[Tuple[Any, ...]]:
    r = _rng()
    rows: List[Tuple[Any, ...]] = []
    for ts in _hour_series(HOURS_MAIN):
        hod = ts.hour
        base_nl = 2800.0 + 900.0 * math.sin(hod / 24 * math.pi) + r.gauss(0, 220.0)
        base_fr = 1900.0 + r.gauss(0, 180.0)
        base_pl = -520.0 + r.gauss(0, 190.0)
        rows.append((ts, "DE", "NL", "export" if base_nl >= 0 else "import", round(base_nl, 1)))
        rows.append((ts, "DE", "FR", "export" if base_fr >= 0 else "import", round(base_fr, 1)))
        rows.append((ts, "DE", "PL", "export" if base_pl >= 0 else "import", round(base_pl, 1)))
        rows.append((ts, "DE", "CZ", "export", round(max(0.0, 400.0 + r.gauss(0, 120.0)), 1)))
    return rows


def forecasts_load_gen_rows() -> List[Tuple[Any, ...]]:
    r = _rng()
    rows: List[Tuple[Any, ...]] = []
    for ts in _hour_series(HOURS_MAIN):
        hod, dow = ts.hour, ts.weekday()
        load_f = (
            53_200.0
            + 8_800.0 * math.exp(-((hod - 8.8) ** 2) / 14.0)
            + 7_200.0 * math.exp(-((hod - 18.5) ** 2) / 16.0)
            + (2_100.0 if dow < 5 else -3_900.0)
            + r.gauss(0, 420.0)
        )
        wind_f = max(800.0, 14_500.0 + 11_000.0 * (0.5 + 0.5 * math.sin((ts.timetuple().tm_yday + hod) / 18.0)) + r.gauss(0, 380.0))
        solar_f = max(0.0, 35_000.0 * math.exp(-((hod - 13.0) ** 2) / 22.0) + r.gauss(0, 700.0))
        res = load_f - wind_f - solar_f
        rows.append(
            (ts, "DE-LU", "stack-load-res-v3", round(load_f, 1), round(wind_f, 1), round(solar_f, 1), round(res, 1))
        )
    return rows


def forecasts_market_prices_rows() -> List[Tuple[Any, ...]]:
    r = _rng()
    rows: List[Tuple[Any, ...]] = []
    for ts in _hour_series(HOURS_MAIN):
        de = _da_price_de_lu_eur_mwh(ts, r)
        for product, bump, vol in [
            ("EPEX_DA_HR", 0.0, 9.0),
            ("EPEX_ID_XBID_15m", 1.8 + r.gauss(0, 2.2), 11.5),
            ("imbalance_de", 3.2 + r.gauss(0, 2.8), 14.0),
        ]:
            mid = max(-200.0, min(450.0, de + bump + r.gauss(0, 3.0)))
            spread_low = 7.0 + vol * 0.35
            spread_high = 11.0 + vol * 0.45
            q10 = round(mid - spread_low - abs(r.gauss(0, 2)), 2)
            q90 = round(mid + spread_high + abs(r.gauss(0, 2.5)), 2)
            imb_idx = round(max(0.0, 0.12 * abs(mid) ** 0.5 / 10.0 + r.gauss(0, 0.25)), 3)
            rows.append((ts, "DE-LU", product, round(mid, 2), q10, q90, imb_idx))
    return rows


def carbon_spark_rows() -> List[Tuple[Any, ...]]:
    r = _rng()
    rows: List[Tuple[Any, ...]] = []
    for i in range(90):
        ts = DEMO_START + dt.timedelta(days=i)
        ets = round(68.0 + 12.0 * math.sin((i + 20) / 365.25 * 2 * math.pi) + r.gauss(0, 2.1), 2)
        goo = round(2.5 + r.gauss(0, 0.35), 2)
        ttf = round(32.0 + 8.0 * math.sin((i + 40) / 365.25 * math.pi) + r.gauss(0, 1.2), 2)
        spark = round(max(5.0, 38.0 + 0.45 * ets + 0.22 * ttf + r.gauss(0, 2.0)), 2)
        rows.append((ts, "DE-LU", ets, goo, ttf, spark))
    return rows


def backtest_metrics_rows() -> List[Tuple[Any, ...]]:
    r = _rng()
    products = ["EPEX_DA_HR", "EPEX_ID_XBID_15m", "imbalance_de", "load_mw"]
    horizons = ["h+1", "h+6", "h+12", "h+24", "h+36", "h+72"]
    rows: List[Tuple[Any, ...]] = []
    for w in range(1, 14):
        run_id = f"br-2024w{w:02d}"
        for prod in products:
            for hz in horizons:
                mae = max(0.5, (2.1 + r.random() * 8.0) * (1.15 if "ID" in prod else 1.0))
                rmse = mae * 1.25 + r.random() * 2.0
                mape = None if prod == "load_mw" else round(0.04 + r.random() * 0.08, 3)
                skill = round(0.95 + r.random() * 0.22, 2)
                pinball = None if prod == "load_mw" else round(1.0 + r.random() * 0.35, 2)
                rows.append(
                    (run_id, "stack-v3", prod, "DE-LU", hz, round(mae, 2), round(rmse, 2), mape, skill, pinball)
                )
    return rows


def drift_metrics_rows() -> List[Tuple[Any, ...]]:
    r = _rng()
    rows: List[Tuple[Any, ...]] = []
    for i in range(13):
        d = (DEMO_START + dt.timedelta(days=7 * i)).date()
        for prod, base in [("EPEX_DA_HR", 0.11), ("load_mw", 0.07)]:
            psi = min(0.55, max(0.02, base + r.gauss(0, 0.06) + i * 0.008))
            rows.append((d, "stack-v3", prod, "DE-LU", round(psi, 3)))
    return rows


def regime_labels_rows() -> List[Tuple[Any, ...]]:
    return [
        ("reg-high-res", "high_wind", "compressed_spark", "2024-10"),
        ("reg-neg-price", "res_surplus", "neg_hours_cluster", "2024-10"),
        ("reg-cold", "high_load", "thermal_margin_tight", "2024-11"),
        ("reg-dunkel", "low_res", "residual_peak", "2024-12"),
        ("reg-import", "tight_atc", "nl_spread_wide", "2024-10"),
        ("reg-gas-spike", "neutral_res", "clean_spark_volatile", "2024-11"),
    ]


def viz_series_long_rows() -> List[Tuple[Any, ...]]:
    r = _rng()
    rows: List[Tuple[Any, ...]] = []
    for ts in _hour_series(HOURS_MAIN):
        de = _da_price_de_lu_eur_mwh(ts, r)
        spread_nl = _nl_spread_vs_de(de, ts, r)
        vol = 3.8 + 2.2 * abs(math.sin(_doy(ts) / 55.0)) + r.gauss(0, 0.35)
        for series, unit, val in [
            ("EPEX_DA_HR", "EUR/MWh", round(de, 3)),
            ("loc_spread_DE-LU_minus_NL", "EUR/MWh", round(-spread_nl, 3)),
            ("implied_vol_DA_30d", "EUR/MWh/sqrt(h)", round(vol, 3)),
        ]:
            rows.append((ts, "DE-LU", series, unit, val))
    return rows


def forecast_vs_actual_rows() -> List[Tuple[Any, ...]]:
    r = _rng()
    rows: List[Tuple[Any, ...]] = []
    for ts in _hour_series(HOURS_MAIN):
        de = _da_price_de_lu_eur_mwh(ts, r)
        fcast = de + r.gauss(0, 3.8)
        act = de + r.gauss(1.2, 4.5)
        ens = 4.0 + r.random() * 9.0
        rows.append(
            (ts, "DE-LU", "EPEX_DA_HR", round(fcast, 2), round(act, 2), round(act - fcast, 2), round(ens, 2))
        )
    return rows


def alert_rules_rows() -> List[Tuple[Any, ...]]:
    return [
        ("r-da-cap", "EPEX_DA_HR", "above", 195.0, "DE-LU", "EUR/MWh", "active"),
        ("r-da-floor", "EPEX_DA_HR", "below", -65.0, "DE-LU", "EUR/MWh", "active"),
        ("r-spread-denl", "loc_spread_DE-LU_minus_NL", "above", 18.0, "DE-LU", "EUR/MWh", "active"),
        ("r-mae", "model_mae", "above", 5.2, "DE-LU", "EUR/MWh", "active"),
        ("r-imb-idx", "imbalance_risk_index", "above", 2.8, "DE-LU", "index", "active"),
        ("r-drift-psi", "feature_drift_psi", "above", 0.35, "DE-LU", "psi", "active"),
    ]


def alert_events_rows() -> List[Tuple[Any, ...]]:
    base = DEMO_START + dt.timedelta(days=5)
    return [
        ("e-001", base + dt.timedelta(hours=7, minutes=22), "r-mae", "HIGH", "DA MAE vs 30d baseline breached"),
        ("e-002", base + dt.timedelta(days=2, hours=11), "r-spread-denl", "WARN", "DE-LU vs NL locational spread elevated"),
        ("e-003", base + dt.timedelta(days=4, hours=15, minutes=40), "r-da-floor", "INFO", "Negative DA hour cluster — check RES forecast"),
        ("e-004", base + dt.timedelta(days=8, hours=6), "r-drift-psi", "WARN", "Feature drift PSI above threshold on ID model"),
        ("e-005", base + dt.timedelta(days=11, hours=9, minutes=5), "r-imb-idx", "HIGH", "Imbalance risk index spike ahead of evening ramp"),
    ]


def dashboard_kpis_rows() -> List[Tuple[Any, ...]]:
    r = _rng()
    rows: List[Tuple[Any, ...]] = []
    for m in range(10, 13):
        month = f"2024-{m:02d}"
        rows.append((month, "forecast_mae_da", "DE-LU", round(2.85 + r.gauss(0, 0.35), 2), "EUR/MWh"))
        rows.append((month, "mark_sensitivity_eur", "DE-LU", round(162_000.0 + r.gauss(0, 12_000.0), 1), "EUR per 1 EUR/MWh DA"))
        rows.append((month, "forecast_consumption_rate", "DE-LU", round(0.86 + r.gauss(0, 0.03), 2), "ratio"))
        rows.append((month, "ensemble_spread_p90", "DE-LU", round(8.2 + r.gauss(0, 0.8), 2), "EUR/MWh"))
    return rows


def tso_market_events_rows() -> List[Tuple[Any, ...]]:
    return [
        (DEMO_START + dt.timedelta(days=2, hours=5, minutes=10), "TenneT", "TSO", "Redispatch volume elevated — north corridor"),
        (DEMO_START + dt.timedelta(days=3, hours=14, minutes=25), "EPEX", "Market", "XBID maintenance window announced"),
        (DEMO_START + dt.timedelta(days=5, hours=8, minutes=50), "Amprion", "TSO", "Wind feed-in forecast revised +6% D+1"),
        (DEMO_START + dt.timedelta(days=7, hours=11), "50Hertz", "TSO", "Ancillary service procurement update"),
        (DEMO_START + dt.timedelta(days=9, hours=16, minutes=40), "ENTSO-E", "Transparency", "Cross-border ATC revision NL-DE"),
        (DEMO_START + dt.timedelta(days=12, hours=7, minutes=15), "EPEX", "Market", "IDA coupling delay resolved — normal operation"),
    ]


def forecast_scope_catalog_rows() -> List[Tuple[Any, ...]]:
    return [
        ("fs-da-de-lu", "point", "bid_curve", "EPEX_DA_HR", "DE-LU", "active"),
        ("fs-id-xbid", "probabilistic", "intraday_position", "EPEX_ID_XBID", "DE-LU", "active"),
        ("fs-imb", "probabilistic", "imbalance_exposure", "imbalance_de", "DE-LU", "active"),
        ("fs-load", "point", "nomination", "load_mw", "DE-LU", "active"),
        ("fs-spread-denl", "point", "spread_trade", "loc_spread_EUR_MWh", "DE-LU_vs_NL", "active"),
        ("fs-residual", "probabilistic", "storage_optimisation", "residual_load_mw", "DE-LU", "pilot"),
        ("fs-go", "point", "forward_mark", "GOO_premium", "DE-LU", "active"),
    ]


def scenario_definitions_rows() -> List[Tuple[Any, ...]]:
    return [
        ("scn-base", "Central", "Median RES; typical weather; ATC open"),
        ("scn-dunkel", "Dunkelflaute", "Low wind & solar; residual load +12–18 GW vs base"),
        ("scn-neg", "Negative price hours", "High RES surplus; DA floor hours clustered"),
        ("scn-import", "Import-constrained", "Tight ATC NL/FR; locational spreads widen"),
        ("scn-gas", "Gas-led spark", "TTF shock + clean spark re-rating"),
        ("scn-cold", "Cold snap", "Load +8%; thermal must-run constraints"),
    ]


def user_personas_rows() -> List[Tuple[Any, ...]]:
    return [
        ("desk-st", "short_term_trader", False),
        ("desk-opt", "optimisation_analyst", False),
        ("comm-b2b", "commercial_b2b", True),
        ("risk-mid", "risk_middle_office", False),
        ("desk-struct", "structured_products", False),
    ]


def downstream_export_rows() -> List[Tuple[Any, ...]]:
    catalog, schema = "energy_utilities", "energy_trading2"
    base = DEMO_START
    return [
        (
            "exp-001",
            "unit_commitment_optimizer",
            "fs-da-de-lu",
            base + dt.timedelta(hours=12),
            "completed",
            f"{catalog}.{schema}.demo_forecasts_market_prices",
            "1.3.0",
        ),
        (
            "exp-002",
            "nomination_desk",
            "fs-load",
            base + dt.timedelta(days=1, hours=6),
            "completed",
            f"{catalog}.{schema}.demo_forecasts_load_gen",
            "1.3.0",
        ),
        (
            "exp-003",
            "b2b_pricing_curves",
            "fs-imb",
            base + dt.timedelta(days=2, hours=14),
            "completed",
            f"{catalog}.{schema}.demo_forecasts_market_prices",
            "1.2.1",
        ),
        (
            "exp-004",
            "portfolio_risk_engine",
            "fs-spread-denl",
            base + dt.timedelta(days=3, hours=9),
            "pending",
            f"{catalog}.{schema}.demo_viz_series_long",
            "1.1.0",
        ),
        (
            "exp-005",
            "hedge_desk_batch",
            "fs-da-de-lu",
            base + dt.timedelta(days=4, hours=11),
            "running",
            f"{catalog}.{schema}.demo_forecast_vs_actual",
            "1.3.0",
        ),
    ]


def consumer_contracts_rows() -> List[Tuple[Any, ...]]:
    return [
        ("unit_commitment_optimizer", "v2.1", "accepted", "Hourly €/MWh + q10/q90; JSON bulk"),
        ("nomination_desk", "v1.4", "accepted", "MW load & RES; 15m cadence optional"),
        ("b2b_pricing_curves", "v3.0", "in_review", "Forward months + implied vol surface"),
        ("portfolio_risk_engine", "v1.0", "accepted", "Long-format series + scenario tags"),
        ("hedge_desk_batch", "v2.0", "accepted", "FvA deltas + ensemble spread"),
    ]


def chart_da_de_lu_series(n_hours: int = 72) -> Tuple[List[int], List[float]]:
    r = random.Random(RNG_SEED)
    prices: List[float] = []
    for h in range(n_hours):
        ts = DEMO_START + dt.timedelta(hours=h)
        prices.append(round(_da_price_de_lu_eur_mwh(ts, r), 2))
    return list(range(n_hours)), prices


def chart_da_rolling_mean_eur_mwh(n_hours: int = 72, window: int = 24) -> Tuple[List[int], List[float], List[float]]:
    x, y = chart_da_de_lu_series(n_hours)
    roll: List[float] = []
    for i in range(n_hours):
        lo = max(0, i - window + 1)
        roll.append(round(sum(y[lo : i + 1]) / (i - lo + 1), 2))
    return x, y, roll


def nl_de_spread_range_eur_mwh(n_hours: int = 168) -> Tuple[float, float]:
    r = random.Random(RNG_SEED)
    spreads: List[float] = []
    for h in range(n_hours):
        ts = DEMO_START + dt.timedelta(hours=h)
        de = _da_price_de_lu_eur_mwh(ts, r)
        nl = de + _nl_spread_vs_de(de, ts, r)
        spreads.append(nl - de)
    return min(spreads), max(spreads)
