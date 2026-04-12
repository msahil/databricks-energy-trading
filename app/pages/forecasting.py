"""
Forecasting & predictive analytics — overview (capability 03).

Binds to `03_forecasting_and_predictive_analytics.ipynb` tables; see
`modules/forecasting/features/03-forecasting-and-predictive-analytics.md`.
"""

from __future__ import annotations

import dash
from dash import Input, Output, callback, dcc, html

import m01_common as m1
import m03_common as m3
import shared_ui as su
import uc_sql as uq

dash.register_page(
    __name__,
    path="/forecasting",
    name="Forecasting overview",
    title="Energy Trading — Forecasting overview",
    order=20,
)

layout = m3.page_shell(
    h1="Forecasting & predictive analytics",
    blurb="""This capability is where **governed models** meet **market timing**: **fundamentals** (load and renewables), **probabilistic price** views with **quantile bands**, **backtest skill** versus baselines, and **drift** monitoring so risk knows when inputs have shifted. The overview below stitches together the **six demo forecast tables** so quant, trading, and operations can **orient** before opening the specialised routes in the sidebar.

Use it for a **morning-style** read: are fundamentals and price layers **aligned**, how tight are **uncertainty bands**, and are **PSI-style** drift metrics still in a comfortable band—**all synthetic**, but structured like a production **forecast hub**.

- **Fundamentals strip** — load, wind, solar, and **residual** from the hourly stack model output.
- **Price layer** — day-ahead **mid** with **q10–q90** fan for the main auction product plus **mid traces** for intraday and imbalance-style rows.
- **Carbon / spark** — daily EUA, TTF, and a **clean spark proxy** for thermal margin stories.
- **Skill snapshot** — average **skill score** and **MAE** from the backtest grid for a quick benchmark read.
- **Regime card** — structural **labels** (metadata) that document known **storylines** in the demo period.

*All series are synthetic demo outputs—not vendor forecasts or operational model scores. Choose a running warehouse in the header.*
""",
    content_id="forecasting-content",
    footnote=(
        "Sources: `demo_forecasts_load_gen`, `demo_forecasts_market_prices`, `demo_carbon_spark_daily`, "
        "`demo_backtest_metrics`, `demo_regime_labels` — see capability 03 spec."
    ),
)


@callback(
    Output("forecasting-content", "children"),
    Input("sql-warehouse-dropdown", "value"),
)
def _render_forecasting(warehouse_id: str | None) -> html.Div:
    if not warehouse_id:
        return m1.select_warehouse_prompt()

    cat, sch = uq.default_catalog_schema()
    t_lg = uq.full_table(cat, sch, "demo_forecasts_load_gen")
    t_mp = uq.full_table(cat, sch, "demo_forecasts_market_prices")
    t_c = uq.full_table(cat, sch, "demo_carbon_spark_daily")
    t_bt = uq.full_table(cat, sch, "demo_backtest_metrics")
    t_rg = uq.full_table(cat, sch, "demo_regime_labels")

    q_lg = f"""
        SELECT ts, load_fcast_mw, wind_fcast_mw, solar_fcast_mw, residual_mw
        FROM {t_lg}
        ORDER BY ts DESC
        LIMIT 336
    """
    r_lg = uq.run_sql(warehouse_id, q_lg, row_limit=400)
    if r_lg.ok and r_lg.rows:
        fig_lg = m3.fig_load_gen_stack(r_lg.rows)
    else:
        fig_lg = m1.empty_fig("Load & renewables forecasts", r_lg.error or "No data")

    q_kpi_l = f"SELECT load_fcast_mw FROM {t_lg} ORDER BY ts DESC LIMIT 1"
    r_kl = uq.run_sql(warehouse_id, q_kpi_l)
    if r_kl.ok and r_kl.rows:
        try:
            lv = float(r_kl.rows[0][0]) if r_kl.rows[0][0] not in ("", None) else None
        except (TypeError, ValueError):
            lv = None
        k_l = f"{lv:,.0f} MW" if lv is not None else "—"
        k_lh = "Latest `load_fcast_mw` — `demo_forecasts_load_gen`"
    else:
        k_l = "—"
        k_lh = (r_kl.error or "?")[:80]

    q_fan = f"""
        SELECT ts, mid_eur_mwh, q10_eur_mwh, q90_eur_mwh
        FROM {t_mp}
        WHERE zone = 'DE-LU' AND product = 'EPEX_DA_HR'
        ORDER BY ts DESC
        LIMIT 168
    """
    r_fan = uq.run_sql(warehouse_id, q_fan, row_limit=300)
    if r_fan.ok and r_fan.rows:
        fig_fan = m3.fig_price_fan_da(r_fan.rows)
    else:
        fig_fan = m1.empty_fig("DA price fan", r_fan.error or "No data")

    q_mid = f"""
        SELECT mid_eur_mwh FROM {t_mp}
        WHERE zone = 'DE-LU' AND product = 'EPEX_DA_HR'
        ORDER BY ts DESC LIMIT 1
    """
    r_mid = uq.run_sql(warehouse_id, q_mid)
    if r_mid.ok and r_mid.rows:
        try:
            mv = float(r_mid.rows[0][0]) if r_mid.rows[0][0] not in ("", None) else None
        except (TypeError, ValueError):
            mv = None
        k_m = f"€{mv:.2f}/MWh" if mv is not None else "—"
        k_mh = "Latest DA mid — `demo_forecasts_market_prices`"
    else:
        k_m = "—"
        k_mh = (r_mid.error or "?")[:80]

    q_carb = f"""
        SELECT ts, zone, eua_eur_t, goo_eur_mwh, ttf_eur_mwh, clean_spark_proxy
        FROM {t_c}
        ORDER BY ts DESC
        LIMIT 90
    """
    r_carb = uq.run_sql(warehouse_id, q_carb, row_limit=120)
    if r_carb.ok and r_carb.rows:
        fig_c = m3.fig_carbon_spark(r_carb.rows)
    else:
        fig_c = m1.empty_fig("Carbon / spark", r_carb.error or "No data")

    q_skill = f"""
        SELECT AVG(skill) AS s, AVG(mae) AS m FROM {t_bt}
        WHERE product <> 'load_mw'
    """
    r_sk = uq.run_sql(warehouse_id, q_skill)
    if r_sk.ok and r_sk.rows:
        s, mm = r_sk.rows[0][:2]
        try:
            sv = float(s) if s not in ("", None) else None
        except (TypeError, ValueError):
            sv = None
        try:
            mv = float(mm) if mm not in ("", None) else None
        except (TypeError, ValueError):
            mv = None
        k_s = f"{sv:.2f}" if sv is not None else "—"
        k_sh = "Mean `skill` — backtest grid (non-load products)"
        k_b = f"{mv:.2f}" if mv is not None else "—"
        k_bh = "Mean `mae` — same filter"
    else:
        k_s = "—"
        k_sh = (r_sk.error or "?")[:80]
        k_b = "—"
        k_bh = "—"

    q_long = f"""
        SELECT ts, product, mid_eur_mwh
        FROM {t_mp}
        WHERE zone = 'DE-LU'
        ORDER BY ts DESC
        LIMIT 504
    """
    r_long = uq.run_sql(warehouse_id, q_long, row_limit=600)
    if r_long.ok and r_long.rows:
        ser = m1.series_from_long_rows(r_long.rows, ts_col=0, name_col=1, val_col=2)
        fig_p = m1.fig_multiline_named(
            ser,
            title="Price forecast mid — by product (DE-LU)",
            y_title="€/MWh",
            x_title="Time",
        )
    else:
        fig_p = m1.empty_fig("Price mids by product", r_long.error or "No data")

    q_rg = f"SELECT regime_id, driver, effect, month_tag FROM {t_rg} ORDER BY month_tag, regime_id"
    r_rg = uq.run_sql(warehouse_id, q_rg, row_limit=50)

    return html.Div(
        className="space-y-8",
        children=[
            html.Div(
                className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4",
                children=[
                    su.stat_card("Latest load forecast", k_l, k_lh),
                    su.stat_card("Latest DA mid", k_m, k_mh),
                    su.stat_card("Mean skill (backtest)", k_s, k_sh),
                    su.stat_card("Mean MAE (backtest)", k_b, k_bh),
                ],
            ),
            html.Div(
                className="grid gap-6 lg:grid-cols-2",
                children=[
                    html.Div(
                        className="chart-panel p-6",
                        children=[
                            dcc.Graph(figure=fig_lg, config={"displayModeBar": False}, className="-mx-2"),
                            html.P(
                                "`demo_forecasts_load_gen` — stack model id in table; zone DE-LU.",
                                className="mt-2 text-xs text-slate-500",
                            ),
                        ],
                    ),
                    html.Div(
                        className="chart-panel p-6",
                        children=[
                            dcc.Graph(figure=fig_fan, config={"displayModeBar": False}, className="-mx-2"),
                            html.P(
                                "`demo_forecasts_market_prices` — EPEX_DA_HR mid with q10/q90 band.",
                                className="mt-2 text-xs text-slate-500",
                            ),
                        ],
                    ),
                ],
            ),
            html.Div(
                className="chart-panel p-6",
                children=[
                    dcc.Graph(figure=fig_p, config={"displayModeBar": False}, className="-mx-2"),
                    html.P(
                        "Compare products on the same clock — DA, intraday-style, imbalance index row.",
                        className="mt-2 text-xs text-slate-500",
                    ),
                ],
            ),
            html.Div(
                className="grid gap-6 lg:grid-cols-2",
                children=[
                    html.Div(
                        className="chart-panel p-6",
                        children=[
                            dcc.Graph(figure=fig_c, config={"displayModeBar": False}, className="-mx-2"),
                            html.P(
                                "`demo_carbon_spark_daily` — GOO shown in detail pages if needed.",
                                className="mt-2 text-xs text-slate-500",
                            ),
                        ],
                    ),
                    html.Div(
                        className="card-elevated overflow-x-auto p-4",
                        children=[
                            html.H2("Regime labels (metadata)", className="mb-3 text-sm font-semibold text-slate-900"),
                            m1.sql_html_table(
                                r_rg,
                                caption="`demo_regime_labels` — narrative tags for structural stories (synthetic).",
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )
