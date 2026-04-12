"""§4.2 — Ingestion: system & transparency (demo Delta)."""

from __future__ import annotations

import dash
from dash import Input, Output, callback, dcc, html

import m01_common as m1
import uc_sql as uq

dash.register_page(
    __name__,
    path="/market-data/system",
    name="M01 system",
    title="Energy Trading — System & transparency",
    order=3,
)

layout = m1.page_shell(
    h1="System & transparency",
    blurb="""Short-term traders and **system operators** care about what the grid actually publishes: **realised load**, **renewable output**, **imbalance prices**, and **ancillary or system signals**. This page bundles those transparency-style views so you can explain **why** the spot might be moving—renewables ramping, tight balance, or expensive imbalance—and how **German imbalance settlement** shapes long versus short exposure.

It is **not** a replacement for a live TSO terminal; it is a structured way to **tell the story** of system and transparency data alongside the price pages, using the same warehouse-backed demo series.

- **Transparency actuals** — load and renewables where published, to anchor fundamentals discussions.
- **Imbalance paths** — long vs short settlement shapes for Germany-style imbalance storytelling.
- **TSO signals** — ancillary-style prices and published wind and solar snapshots for operational context.
- **Operations use** — a single place to rehearse how you would brief **short-term risk** and **balancing** exposure.
- **Price linkage** — read this after **Prices** when you need the “why” behind the spot, not just the level.

*Synthetic demo series shaped like public transparency—not operational or real-time TSO feeds.*
""",
    content_id="m01-system-body",
    footnote=(
        "Sources: `demo_entsoe_transparency_style`, `demo_german_imbalance_prices_style`, `demo_grid_signals`."
    ),
)


@callback(
    Output("m01-system-body", "children"),
    Input("sql-warehouse-dropdown", "value"),
)
def _render(warehouse_id: str | None) -> html.Div:
    if not warehouse_id:
        return m1.select_warehouse_prompt()

    cat, sch = uq.default_catalog_schema()
    te = uq.full_table(cat, sch, "demo_entsoe_transparency_style")
    tg = uq.full_table(cat, sch, "demo_german_imbalance_prices_style")
    tgr = uq.full_table(cat, sch, "demo_grid_signals")

    qe = f"""
        SELECT timestamp_utc, series_name, value
        FROM {te}
        WHERE series_name IN (
            'Actual Total Load',
            'Actual Generation Wind Onshore',
            'Actual Generation Solar'
        )
        ORDER BY timestamp_utc DESC
        LIMIT 504
    """
    re = uq.run_sql(warehouse_id, qe, row_limit=600)
    if re.ok and re.rows:
        ser_e = m1.series_from_long_rows(re.rows, ts_col=0, name_col=1, val_col=2)
        fig_e = m1.fig_multiline_named(
            ser_e,
            title="Load and renewables — transparency-style actuals (DE-LU area)",
            y_title="MW",
            x_title="Time (UTC)",
            colors=("#0f172a", "#0284c7", "#f59e0b"),
        )
    else:
        fig_e = m1.empty_fig("ENTSO-E style series", re.error or "No data")

    qg = f"""
        SELECT timestamp_utc, price_type, AVG(eur_per_mwh) AS eur_per_mwh
        FROM {tg}
        GROUP BY timestamp_utc, price_type
        ORDER BY timestamp_utc DESC
        LIMIT 336
    """
    rg = uq.run_sql(warehouse_id, qg, row_limit=400)
    if rg.ok and rg.rows:
        ser_g = m1.series_from_long_rows(rg.rows, ts_col=0, name_col=1, val_col=2)
        fig_g = m1.fig_multiline_named(
            ser_g,
            title="German imbalance — long vs short (averaged across TSOs)",
            y_title="€/MWh",
            x_title="Time (UTC)",
            colors=("#b91c1c", "#15803d"),
        )
    else:
        fig_g = m1.empty_fig("Imbalance", rg.error or "No data")

    q_afrr = f"""
        SELECT ts, tso, value
        FROM {tgr}
        WHERE metric = 'aFRR_capacity_price'
        ORDER BY ts DESC
        LIMIT 672
    """
    r_afrr = uq.run_sql(warehouse_id, q_afrr, row_limit=800)
    if r_afrr.ok and r_afrr.rows:
        ser_a = m1.series_from_long_rows(r_afrr.rows, ts_col=0, name_col=1, val_col=2)
        fig_a = m1.fig_multiline_named(
            ser_a,
            title="aFRR capacity price — by German TSO",
            y_title="EUR/MW/h",
            x_title="Time",
        )
    else:
        fig_a = m1.empty_fig("aFRR", r_afrr.error or "No data")

    q_res = f"""
        SELECT ts, metric, value
        FROM {tgr}
        WHERE metric IN ('wind_onshore_actual', 'solar_actual_est')
        ORDER BY ts DESC
        LIMIT 336
    """
    r_res = uq.run_sql(warehouse_id, q_res, row_limit=400)
    if r_res.ok and r_res.rows:
        ser_r = m1.series_from_long_rows(r_res.rows, ts_col=0, name_col=1, val_col=2)
        fig_r = m1.fig_multiline_named(
            ser_r,
            title="Published wind and solar output — selected TSO metrics",
            y_title="MW",
            x_title="Time",
            colors=("#0369a1", "#d97706"),
        )
    else:
        fig_r = m1.empty_fig("RES actuals", r_res.error or "No data")

    return html.Div(
        className="space-y-8",
        children=[
            html.Div(
                className="chart-panel p-6",
                children=[
                    dcc.Graph(figure=fig_e, config={"displayModeBar": False}),
                    html.P(
                        "Load, onshore wind, and solar (synthetic). `demo_entsoe_transparency_style`.",
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
                            dcc.Graph(figure=fig_g, config={"displayModeBar": False}),
                            html.P(
                                "Long vs short imbalance paths, hourly mean across control areas. `demo_german_imbalance_prices_style`.",
                                className="mt-2 text-xs text-slate-500",
                            ),
                        ],
                    ),
                    html.Div(
                        className="chart-panel p-6",
                        children=[
                            dcc.Graph(figure=fig_a, config={"displayModeBar": False}),
                            html.P(
                                "Ancillary price exposure by TSO. `demo_grid_signals` · `aFRR_capacity_price`.",
                                className="mt-2 text-xs text-slate-500",
                            ),
                        ],
                    ),
                ],
            ),
            html.Div(
                className="chart-panel p-6",
                children=[
                    dcc.Graph(figure=fig_r, config={"displayModeBar": False}),
                    html.P(
                        "Illustrative RES output series (synthetic). `demo_grid_signals` — onshore wind vs solar estimate.",
                        className="mt-2 text-xs text-slate-500",
                    ),
                ],
            ),
        ],
    )
