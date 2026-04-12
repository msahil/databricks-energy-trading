"""
Strategy, optimisation & algo trading — overview (capability 04).

See `modules/forecasting/features/04-strategy-optimisation-and-algorithmic-trading.md`.
"""

from __future__ import annotations

import dash
from dash import Input, Output, callback, dcc, html

import m01_common as m1
import m02_common as m2
import m04_common as m4
import shared_ui as su
import uc_sql as uq

dash.register_page(
    __name__,
    path="/strategy",
    name="Strategy overview",
    title="Energy Trading — Strategy overview",
    order=30,
)

layout = m4.page_shell(
    h1="Strategy, optimisation & algo trading",
    blurb="""This capability ties together **parameterised strategies**, **backtest evidence**, **operational KPIs**, **alerts**, and **market context** so research and production controls feel like **one product**. The overview below samples the **eleven demo tables** from notebook **04**: long-format **series** for charting, **forecast vs actual** paths for skill review, **strategy** and **backtest** rows for governance, and a **slice of alerts** so incident language is never abstract.

Use it to **onboard** a stakeholder: what is **paper vs shadow**, how **PnL and Sharpe** look in synthetic runs, and which **alert rules** would fire when prices, spreads, or drift move—**all illustrative**, but structured like a **desk + risk** briefing.

- **Market series** — DA price, locational spread, and implied vol from the **long** demo series.
- **Forecast quality** — **forecast vs actual** and **hourly error** for the main power product.
- **Strategies** — definitions with **deployment mode** (paper / shadow / pilot vocabulary).
- **Backtest** — **net PnL** and **Sharpe** snapshot from the summary table.
- **Alerts** — recent **synthetic events** with **severity** for monitoring narrative.

*Synthetic operations data—not live strategies, orders, or exchange connectivity.*
""",
    content_id="strategy-content",
    footnote=(
        "Sources: `demo_viz_series_long`, `demo_forecast_vs_actual`, `demo_strategy_definitions`, "
        "`demo_backtest_summary`, `demo_alert_events` — capability 04 notebook."
    ),
)


@callback(
    Output("strategy-content", "children"),
    Input("sql-warehouse-dropdown", "value"),
)
def _render_strategy(warehouse_id: str | None) -> html.Div:
    if not warehouse_id:
        return m1.select_warehouse_prompt()

    cat, sch = uq.default_catalog_schema()
    t_viz = uq.full_table(cat, sch, "demo_viz_series_long")
    t_fva = uq.full_table(cat, sch, "demo_forecast_vs_actual")
    t_st = uq.full_table(cat, sch, "demo_strategy_definitions")
    t_bt = uq.full_table(cat, sch, "demo_backtest_summary")
    t_ae = uq.full_table(cat, sch, "demo_alert_events")
    t_kpi = uq.full_table(cat, sch, "demo_dashboard_kpis")

    q_viz = f"""
        SELECT ts, series, value
        FROM {t_viz}
        WHERE zone = 'DE-LU'
        ORDER BY ts DESC
        LIMIT 504
    """
    r_viz = uq.run_sql(warehouse_id, q_viz, row_limit=600)
    if r_viz.ok and r_viz.rows:
        ser = m1.series_from_long_rows(r_viz.rows, ts_col=0, name_col=1, val_col=2)
        fig_viz = m1.fig_multiline_named(
            ser,
            title="Long-format market series — DE-LU",
            y_title="Value (see series units in footnote)",
            x_title="Time",
        )
    else:
        fig_viz = m1.empty_fig("Series", r_viz.error or "No data")

    q_fva = f"""
        SELECT ts, forecast_eur_mwh, actual_eur_mwh, error_eur_mwh
        FROM {t_fva}
        WHERE zone = 'DE-LU' AND product = 'EPEX_DA_HR'
        ORDER BY ts DESC
        LIMIT 168
    """
    r_fva = uq.run_sql(warehouse_id, q_fva, row_limit=300)
    if r_fva.ok and r_fva.rows:
        fig_fva = m4.fig_forecast_vs_actual([[r[0], r[1], r[2]] for r in r_fva.rows])
        fig_err = m4.fig_error_series([[r[0], r[3]] for r in r_fva.rows])
    else:
        fig_fva = m1.empty_fig("Forecast vs actual", r_fva.error or "No data")
        fig_err = m1.empty_fig("Error", r_fva.error or "No data")

    q_k1 = f"""
        SELECT value FROM {t_kpi}
        WHERE kpi = 'forecast_mae_da' AND zone = 'DE-LU'
        ORDER BY month DESC
        LIMIT 1
    """
    r_k1 = uq.run_sql(warehouse_id, q_k1)
    if r_k1.ok and r_k1.rows:
        try:
            v = float(r_k1.rows[0][0]) if r_k1.rows[0][0] not in ("", None) else None
        except (TypeError, ValueError):
            v = None
        k1 = f"{v:.2f} €/MWh" if v is not None else "—"
        k1h = "Latest monthly `forecast_mae_da` — `demo_dashboard_kpis`"
    else:
        k1 = "—"
        k1h = (r_k1.error or "?")[:80]

    q_k2 = f"SELECT COUNT(*) FROM {t_st}"
    r_k2 = uq.run_sql(warehouse_id, q_k2)
    n_strat = int(float(r_k2.rows[0][0])) if r_k2.ok and r_k2.rows and r_k2.rows[0][0] not in ("", None) else 0

    q_k3 = f"SELECT SUM(net_pnl_eur_sim) FROM {t_bt}"
    r_k3 = uq.run_sql(warehouse_id, q_k3)
    if r_k3.ok and r_k3.rows:
        try:
            pnl = float(r_k3.rows[0][0]) if r_k3.rows[0][0] not in ("", None) else None
        except (TypeError, ValueError):
            pnl = None
        k3 = f"€{pnl:,.0f}" if pnl is not None else "—"
        k3h = "Sum of `net_pnl_eur_sim` across demo backtests"
    else:
        k3 = "—"
        k3h = (r_k3.error or "?")[:80]

    q_k4 = f"SELECT COUNT(*) FROM {t_ae}"
    r_k4 = uq.run_sql(warehouse_id, q_k4)
    n_al = int(float(r_k4.rows[0][0])) if r_k4.ok and r_k4.rows and r_k4.rows[0][0] not in ("", None) else 0

    q_bt_bar = f"""
        SELECT strategy_id, net_pnl_eur_sim
        FROM {t_bt}
    """
    r_bt = uq.run_sql(warehouse_id, q_bt_bar, row_limit=20)
    if r_bt.ok and r_bt.rows:
        lbs = [str(r[0]) for r in r_bt.rows]
        vals = [float(r[1]) if r[1] not in ("", None) else 0.0 for r in r_bt.rows]
        fig_pnl = m2.fig_bar_categories(
            lbs,
            vals,
            title="Backtest net PnL by strategy (simulated EUR)",
            y_title="€",
            color="#059669",
        )
    else:
        fig_pnl = m1.empty_fig("Backtest PnL", r_bt.error or "No data")

    q_st = f"SELECT * FROM {t_st} ORDER BY strategy_id"
    r_st = uq.run_sql(warehouse_id, q_st, row_limit=20)

    q_ae = f"SELECT event_id, event_ts, rule_id, severity, message FROM {t_ae} ORDER BY event_ts DESC"
    r_ae = uq.run_sql(warehouse_id, q_ae, row_limit=20)

    return html.Div(
        className="space-y-8",
        children=[
            html.Div(
                className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4",
                children=[
                    su.stat_card("Dashboard MAE (latest month)", k1, k1h),
                    su.stat_card("Strategy definitions", str(n_strat), "`demo_strategy_definitions` rows"),
                    su.stat_card("Backtest PnL (sum)", k3, k3h),
                    su.stat_card("Alert events (count)", str(n_al), "`demo_alert_events`"),
                ],
            ),
            html.Div(
                className="chart-panel p-6",
                children=[
                    dcc.Graph(figure=fig_viz, config={"displayModeBar": False}, className="-mx-2"),
                    html.P(
                        "`demo_viz_series_long` — units vary by `series` (DA €/MWh, spread €/MWh, vol).",
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
                            dcc.Graph(figure=fig_fva, config={"displayModeBar": False}, className="-mx-2"),
                            html.P(
                                "`demo_forecast_vs_actual` — EPEX_DA_HR, DE-LU.",
                                className="mt-2 text-xs text-slate-500",
                            ),
                        ],
                    ),
                    html.Div(
                        className="chart-panel p-6",
                        children=[
                            dcc.Graph(figure=fig_err, config={"displayModeBar": False}, className="-mx-2"),
                            html.P(
                                "`error_eur_mwh` — actual minus forecast.",
                                className="mt-2 text-xs text-slate-500",
                            ),
                        ],
                    ),
                ],
            ),
            html.Div(
                className="chart-panel p-6",
                children=[
                    dcc.Graph(figure=fig_pnl, config={"displayModeBar": False}, className="-mx-2"),
                    html.P(
                        "`demo_backtest_summary.net_pnl_eur_sim` per `strategy_id`.",
                        className="mt-2 text-xs text-slate-500",
                    ),
                ],
            ),
            html.Div(
                className="grid gap-6 lg:grid-cols-2",
                children=[
                    html.Div(
                        className="card-elevated overflow-x-auto p-4",
                        children=[
                            html.H2("Strategy definitions", className="mb-3 text-sm font-semibold text-slate-900"),
                            m1.sql_html_table(
                                r_st,
                                caption="`demo_strategy_definitions` — status and deployment mode.",
                            ),
                        ],
                    ),
                    html.Div(
                        className="card-elevated overflow-x-auto p-4",
                        children=[
                            html.H2("Recent alert events", className="mb-3 text-sm font-semibold text-slate-900"),
                            m1.sql_html_table(
                                r_ae,
                                caption="`demo_alert_events` — synthetic severities.",
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )
