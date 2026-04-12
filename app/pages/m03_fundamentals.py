"""Capability 03 — Fundamentals forecasting (load & renewables)."""

from __future__ import annotations

import dash
from dash import Input, Output, callback, dcc, html

import m01_common as m1
import m03_common as m3
import uc_sql as uq

dash.register_page(
    __name__,
    path="/forecasting/fundamentals",
    name="M03 fundamentals",
    title="Energy Trading — Fundamentals forecasts",
    order=21,
)

layout = m3.page_shell(
    h1="Fundamentals forecasting",
    blurb="""Short-term desks need **load** and **renewables** on the **same clock** as prices: total demand, **wind** and **solar** shapes, and the **residual** left for thermal and imports. This page surfaces the **hourly stack** from the demo fundamentals table so traders and analysts can **sanity-check** profiles against **weather narratives** and **transparency** actuals on the Market data routes—without claiming these are **TSO schedules** or **official** forecasts.

Use it when you rehearse **cut-off** stories (what was knowable before gate closure) or when you explain **residual risk** to a stakeholder who is not looking at raw **NWP** grids.

- **Hourly curves** — load, wind, and solar **forecasts** plus **residual** in MW.
- **Single zone** — DE-LU in the synthetic batch to keep the chart legible.
- **Model id** — `model_id` is carried in the table for **registry-style** conversations.
- **Uncertainty** — the demo is **point-style** only; bands would live in an extended pipeline.
- **Linkage** — compare qualitatively with **Weather & commodities** and **System & transparency** pages.

*Synthetic generator output—not an operational load or RES forecast.*
""",
    content_id="m03-fundamentals-body",
    footnote="Source: `demo_forecasts_load_gen` — columns `ts`, `zone`, `model_id`, `load_fcast_mw`, `wind_fcast_mw`, `solar_fcast_mw`, `residual_mw`.",
)


@callback(
    Output("m03-fundamentals-body", "children"),
    Input("sql-warehouse-dropdown", "value"),
)
def _render(warehouse_id: str | None) -> html.Div:
    if not warehouse_id:
        return m1.select_warehouse_prompt()

    cat, sch = uq.default_catalog_schema()
    t = uq.full_table(cat, sch, "demo_forecasts_load_gen")

    q = f"""
        SELECT ts, model_id, load_fcast_mw, wind_fcast_mw, solar_fcast_mw, residual_mw
        FROM {t}
        ORDER BY ts DESC
        LIMIT 720
    """
    r = uq.run_sql(warehouse_id, q, row_limit=800)
    if r.ok and r.rows:
        fig = m3.fig_load_gen_stack([[row[0], row[2], row[3], row[4], row[5]] for row in r.rows])
    else:
        fig = m1.empty_fig("Fundamentals forecasts", r.error or "No data")

    q_meta = f"SELECT DISTINCT model_id, zone FROM {t}"
    r_meta = uq.run_sql(warehouse_id, q_meta, row_limit=20)

    return html.Div(
        className="space-y-8",
        children=[
            html.Div(
                className="chart-panel p-6",
                children=[
                    dcc.Graph(figure=fig, config={"displayModeBar": False}, className="-mx-2"),
                    html.P(
                        "Residual = load − wind − solar in the demo definition.",
                        className="mt-2 text-xs text-slate-500",
                    ),
                ],
            ),
            html.Div(
                className="card-elevated overflow-x-auto p-4",
                children=[
                    html.H2("Model scope", className="mb-3 text-sm font-semibold text-slate-900"),
                    m1.sql_html_table(
                        r_meta,
                        caption="Distinct `model_id` and `zone` in the batch.",
                    ),
                ],
            ),
        ],
    )
