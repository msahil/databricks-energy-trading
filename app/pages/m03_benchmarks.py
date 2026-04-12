"""Capability 03 — Benchmarking & evaluation (backtest metrics)."""

from __future__ import annotations

import dash
from dash import Input, Output, callback, dcc, html

import m01_common as m1
import m02_common as m2
import m03_common as m3
import shared_ui as su
import uc_sql as uq

dash.register_page(
    __name__,
    path="/forecasting/benchmarks",
    name="M03 benchmarks",
    title="Energy Trading — Forecast benchmarks",
    order=23,
)

layout = m3.page_shell(
    h1="Benchmarking & evaluation",
    blurb="""Before a model earns **production promotion**, desks expect **out-of-sample** evidence: **MAE/RMSE** for points, **pinball** when distributions matter, and a **skill** score versus an agreed baseline. The demo **backtest grid** stores **run_id**, **horizon**, **product**, and **zone** so you can **slice** performance the way a **model risk** review would—without running notebooks in the app.

This page highlights **EPEX_DA_HR** error by **forecast horizon** and shows a **sample of rows** so you can **trace** which **weeks** (`run_id`) were simulated.

- **Horizon curve** — average **MAE** by `h+1` … `h+72` for the day-ahead product.
- **Skill** — mean **skill** in the same slice for a one-number **headline**.
- **Full grid** — capped table for **audit-style** scanning across products and horizons.
- **Leakage** — spec requires **walk-forward** validation; demo numbers are **illustrative** only.
- **Vendor** — side-by-side **vendor** forecasts would appear as separate **product** keys when subscribed.

*Synthetic metrics—not a live model certification.*
""",
    content_id="m03-benchmarks-body",
    footnote=(
        "Source: `demo_backtest_metrics` — `run_id`, `model_id`, `product`, `zone`, `horizon`, "
        "`mae`, `rmse`, `mape`, `skill`, `pinball`."
    ),
)


@callback(
    Output("m03-benchmarks-body", "children"),
    Input("sql-warehouse-dropdown", "value"),
)
def _render(warehouse_id: str | None) -> html.Div:
    if not warehouse_id:
        return m1.select_warehouse_prompt()

    cat, sch = uq.default_catalog_schema()
    t = uq.full_table(cat, sch, "demo_backtest_metrics")

    q_hor = f"""
        SELECT horizon, AVG(mae) AS mae_avg, AVG(skill) AS skill_avg
        FROM {t}
        WHERE zone = 'DE-LU' AND product = 'EPEX_DA_HR'
        GROUP BY horizon
        ORDER BY horizon
    """
    r_h = uq.run_sql(warehouse_id, q_hor, row_limit=50)
    if r_h.ok and r_h.rows:
        labs = [str(r[0]) for r in r_h.rows]
        vals = [float(r[1]) if r[1] not in ("", None) else 0.0 for r in r_h.rows]
        fig_mae = m2.fig_bar_categories(
            labs,
            vals,
            title="Mean MAE by horizon — EPEX_DA_HR (DE-LU)",
            y_title="MAE (€/MWh, demo)",
            color="#ff3621",
        )
    else:
        fig_mae = m1.empty_fig("MAE by horizon", r_h.error or "No data")

    q_kpi = f"""
        SELECT AVG(skill) AS s, AVG(pinball) AS p
        FROM {t}
        WHERE zone = 'DE-LU' AND product = 'EPEX_DA_HR' AND pinball IS NOT NULL
    """
    r_k = uq.run_sql(warehouse_id, q_kpi)
    if r_k.ok and r_k.rows:
        s, p = r_k.rows[0][:2]
        try:
            sv = float(s) if s not in ("", None) else None
        except (TypeError, ValueError):
            sv = None
        try:
            pv = float(p) if p not in ("", None) else None
        except (TypeError, ValueError):
            pv = None
        k1 = f"{sv:.3f}" if sv is not None else "—"
        k1h = "Mean skill — DA horizon slice"
        k2 = f"{pv:.3f}" if pv is not None else "—"
        k2h = "Mean pinball — distributional score (demo)"
    else:
        k1 = "—"
        k1h = (r_k.error or "?")[:80]
        k2 = "—"
        k2h = "—"

    q_sample = f"""
        SELECT run_id, model_id, product, zone, horizon, mae, rmse, skill, pinball
        FROM {t}
        ORDER BY run_id DESC, product, horizon
        LIMIT 80
    """
    r_s = uq.run_sql(warehouse_id, q_sample, row_limit=100)

    return html.Div(
        className="space-y-8",
        children=[
            html.Div(
                className="grid gap-4 sm:grid-cols-2",
                children=[
                    su.stat_card("Mean skill (DA slice)", k1, k1h),
                    su.stat_card("Mean pinball (DA slice)", k2, k2h),
                ],
            ),
            html.Div(
                className="chart-panel p-6",
                children=[
                    dcc.Graph(figure=fig_mae, config={"displayModeBar": False}, className="-mx-2"),
                    html.P(
                        "Aggregated across `run_id` weeks for the selected product filter.",
                        className="mt-2 text-xs text-slate-500",
                    ),
                ],
            ),
            html.Div(
                className="card-elevated overflow-x-auto p-4",
                children=[
                    html.H2("Backtest grid (sample rows)", className="mb-3 text-sm font-semibold text-slate-900"),
                    m1.sql_html_table(
                        r_s,
                        caption="`demo_backtest_metrics` — `mape` omitted in table width; full column set in SQL.",
                    ),
                ],
            ),
        ],
    )
