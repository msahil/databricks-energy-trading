"""§4.6 — Analytics & ML on platform data (demo Delta)."""

from __future__ import annotations

import dash
from dash import Input, Output, callback, dcc, html

import m01_common as m1
import uc_sql as uq

dash.register_page(
    __name__,
    path="/market-data/analytics",
    name="M01 analytics",
    title="Energy Trading — Analytics & platform data",
    order=7,
)

layout = m1.page_shell(
    h1="Analytics & ML (on platform data)",
    blurb="""Before anyone trains a model, desks usually ask **descriptive** questions: which zone has been **wide**, **skewed**, or **volatile**, and do **load and residual** line up with the story in the spot? This page surfaces **simple aggregates and distributions**—means, ranges, and load versus residual-style views—so you can **explore** the demo platform data the same way a quant team would **profile** a dataset in a notebook.

Nothing here is **trained or scored** in the app; it is a **read-only** analytics layer on top of the same governed prices and fundamentals tables used elsewhere.

- **Price distribution** — zone-level summaries so you can compare dispersion and extremes at a glance.
- **Product mix** — mean levels by market and product to see where the book might be concentrated in the demo.
- **Load vs residual** — fundamentals pairing for a quick **supply–demand** sanity check against prices.
- **Feature mindset** — mirrors the kind of **feature inspection** you would do before offline ML or forecasting.
- **Scope** — exploratory only; **no** backtest, **no** model serving, **no** optimisation in this route.

*No models run in-app. Illustrative data for profiling and exploration. Source tables are in the footnote.*
""",
    content_id="m01-analytics-body",
    footnote="Sources: `demo_prices_spot_hourly`, `demo_fundamentals_de_lu`.",
)


@callback(
    Output("m01-analytics-body", "children"),
    Input("sql-warehouse-dropdown", "value"),
)
def _render(warehouse_id: str | None) -> html.Div:
    if not warehouse_id:
        return m1.select_warehouse_prompt()

    cat, sch = uq.default_catalog_schema()
    t_p = uq.full_table(cat, sch, "demo_prices_spot_hourly")
    t_f = uq.full_table(cat, sch, "demo_fundamentals_de_lu")

    q_agg = f"""
        SELECT
            bidding_zone,
            COUNT(*) AS n_hours,
            ROUND(MIN(price_eur_mwh), 2) AS min_eur_mwh,
            ROUND(MAX(price_eur_mwh), 2) AS max_eur_mwh,
            ROUND(AVG(price_eur_mwh), 2) AS avg_eur_mwh,
            ROUND(stddev_pop(price_eur_mwh), 2) AS stdev_eur_mwh
        FROM {t_p}
        WHERE product_code = 'EPEX_DA_HR'
        GROUP BY bidding_zone
        ORDER BY bidding_zone
    """
    ra = uq.run_sql(warehouse_id, q_agg, row_limit=100)

    q_prod = f"""
        SELECT product_code, bidding_zone, COUNT(*) AS n, ROUND(AVG(price_eur_mwh), 2) AS avg_eur_mwh
        FROM {t_p}
        GROUP BY product_code, bidding_zone
        ORDER BY product_code, bidding_zone
    """
    rp = uq.run_sql(warehouse_id, q_prod, row_limit=50)

    q_f = f"""
        SELECT ts, load_mw, residual_mw
        FROM {t_f}
        WHERE zone = 'DE-LU'
        ORDER BY ts DESC
        LIMIT 168
    """
    rf = uq.run_sql(warehouse_id, q_f, row_limit=300)
    fig_f = m1.empty_fig("Load vs residual", rf.error or "No data")
    if rf.ok and rf.rows:
        fig_f = m1.fig_two_series(
            [[r[0], r[1], r[2]] for r in rf.rows],
            name_a="load_mw",
            name_b="residual_mw",
            title="DE-LU — system load and residual load proxy",
            y_title="MW",
        )

    return html.Div(
        className="space-y-8",
        children=[
            html.Div(
                className="card-elevated overflow-x-auto p-4",
                children=[
                    html.H2("Day-ahead prices — distribution by zone", className="mb-3 text-sm font-semibold text-slate-900"),
                    m1.sql_html_table(
                        ra,
                        caption="Min / max / average / volatility by zone — `demo_prices_spot_hourly`, day-ahead product.",
                    ),
                ],
            ),
            html.Div(
                className="card-elevated overflow-x-auto p-4",
                children=[
                    html.H2("Mean price by product and zone", className="mb-3 text-sm font-semibold text-slate-900"),
                    m1.sql_html_table(
                        rp,
                        caption="Day-ahead and intraday index where present — `demo_prices_spot_hourly`.",
                    ),
                ],
            ),
            html.Div(
                className="chart-panel p-6",
                children=[
                    dcc.Graph(figure=fig_f, config={"displayModeBar": False}, className="-mx-2"),
                    html.P(
                        "Residual proxies load net of variable renewables for short-term stress views. `demo_fundamentals_de_lu` (synthetic).",
                        className="mt-2 text-xs text-slate-500",
                    ),
                ],
            ),
        ],
    )
