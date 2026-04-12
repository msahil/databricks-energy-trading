"""§4.5 — Marks & curves (demo Delta)."""

from __future__ import annotations

import dash
from dash import Input, Output, callback, dcc, html
import plotly.graph_objects as go

import m01_common as m1
import shared_ui as su
import uc_sql as uq

dash.register_page(
    __name__,
    path="/market-data/marks",
    name="M01 marks",
    title="Energy Trading — Marks & locational spreads",
    order=6,
)

layout = m1.page_shell(
    h1="Marks & curves",
    blurb="""**Locational basis** is how much one bidding zone clears **above or below** another for the same product and delivery. Many books frame risk around **Germany–Luxembourg** as a hub; this page shows **hourly spreads** of the Netherlands and France **against DE-LU day-ahead** so you can discuss **congestion**, **import/export flows**, and **P&L attribution** when a position is split across zones.

In production you would often separate **official internal marks** from **exchange prints**; here the demo uses a **single hourly price series** everywhere so you can focus on the **spread mechanics** without a second marks table.

- **NL vs DE-LU** — hourly spread path for the Dutch–German relationship traders watch for border and congestion stories.
- **FR vs DE-LU** — hourly spread path for the French–German relationship relevant to coupled markets and flows.
- **Same grain** — day-ahead hourly so spreads align with the **Prices** page without mixing products.
- **Latest snapshot** — point-in-time check for quick commentary in meetings or decks.
- **Limitation** — no internal **marks** curve object in the demo; this is **exchange-style** spreads for illustration.

*Derived from the same hourly price series used elsewhere. Demo only—no separate internal marks table.*
""",
    content_id="m01-marks-body",
    footnote="Derived from `demo_prices_spot_hourly` (day-ahead hourly) — no internal marks table in the demo.",
)


def _spread_fig(rows: list[list], *, title: str, fill_color: str) -> go.Figure:
    fig = m1.empty_fig(title, "No data")
    if not rows:
        return fig
    xs: list = []
    ys: list = []
    for row in reversed(rows):
        if len(row) >= 2:
            xs.append(row[0])
            try:
                ys.append(float(row[1]) if row[1] not in ("", None) else None)
            except (TypeError, ValueError):
                ys.append(None)
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=xs,
            y=ys,
            mode="lines",
            line=dict(color="#7c3aed", width=2),
            fill="tozeroy",
            fillcolor=fill_color,
        )
    )
    fig.update_layout(
        title=dict(text=title, font=dict(size=14)),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=340,
        margin=dict(l=0, r=12, t=48, b=40),
        yaxis=dict(title="€/MWh", showgrid=True, gridcolor="#e2e8f0"),
        xaxis=dict(title="delivery_ts", showgrid=True, gridcolor="#e2e8f0"),
        showlegend=False,
        font=dict(family="Inter, ui-sans-serif, system-ui, sans-serif", size=12, color="#475569"),
    )
    return fig


@callback(
    Output("m01-marks-body", "children"),
    Input("sql-warehouse-dropdown", "value"),
)
def _render(warehouse_id: str | None) -> html.Div:
    if not warehouse_id:
        return m1.select_warehouse_prompt()

    cat, sch = uq.default_catalog_schema()
    t_p = uq.full_table(cat, sch, "demo_prices_spot_hourly")

    q_nl = f"""
        SELECT de.delivery_ts, (nl.price_eur_mwh - de.price_eur_mwh) AS nl_minus_de
        FROM
            (SELECT delivery_ts, price_eur_mwh FROM {t_p}
             WHERE bidding_zone = 'DE-LU' AND product_code = 'EPEX_DA_HR') de
        INNER JOIN
            (SELECT delivery_ts, price_eur_mwh FROM {t_p}
             WHERE bidding_zone = 'NL' AND product_code = 'EPEX_DA_HR') nl
        ON de.delivery_ts = nl.delivery_ts
        ORDER BY de.delivery_ts DESC
        LIMIT 168
    """
    r_nl = uq.run_sql(warehouse_id, q_nl, row_limit=300)

    q_fr = f"""
        SELECT de.delivery_ts, (fr.price_eur_mwh - de.price_eur_mwh) AS fr_minus_de
        FROM
            (SELECT delivery_ts, price_eur_mwh FROM {t_p}
             WHERE bidding_zone = 'DE-LU' AND product_code = 'EPEX_DA_HR') de
        INNER JOIN
            (SELECT delivery_ts, price_eur_mwh FROM {t_p}
             WHERE bidding_zone = 'FR' AND product_code = 'EPEX_DA_HR') fr
        ON de.delivery_ts = fr.delivery_ts
        ORDER BY de.delivery_ts DESC
        LIMIT 168
    """
    r_fr = uq.run_sql(warehouse_id, q_fr, row_limit=300)

    fig_nl = _spread_fig(
        r_nl.rows if r_nl.ok else [],
        title="Netherlands vs Germany–Luxembourg — hourly locational spread",
        fill_color="rgba(124, 58, 237, 0.12)",
    )
    if not r_nl.ok:
        fig_nl = m1.empty_fig("NL − DE-LU", r_nl.error or "No data")

    fig_fr = _spread_fig(
        r_fr.rows if r_fr.ok else [],
        title="France vs Germany–Luxembourg — hourly locational spread",
        fill_color="rgba(37, 99, 235, 0.12)",
    )
    if r_fr.ok and r_fr.rows:
        fig_fr.update_traces(line=dict(color="#2563eb"))
    if not r_fr.ok:
        fig_fr = m1.empty_fig("FR − DE-LU", r_fr.error or "No data")

    q_kpi = f"""
        WITH mx AS (
            SELECT MAX(delivery_ts) AS ts FROM {t_p} WHERE product_code = 'EPEX_DA_HR'
        )
        SELECT nl.price_eur_mwh - de.price_eur_mwh AS nl_spread_now
        FROM mx
        INNER JOIN {t_p} de
            ON de.delivery_ts = mx.ts AND de.bidding_zone = 'DE-LU' AND de.product_code = 'EPEX_DA_HR'
        INNER JOIN {t_p} nl
            ON nl.delivery_ts = mx.ts AND nl.bidding_zone = 'NL' AND nl.product_code = 'EPEX_DA_HR'
    """
    rk = uq.run_sql(warehouse_id, q_kpi, row_limit=5)
    kpi_nl = "—"
    if rk.ok and rk.rows and rk.rows[0]:
        try:
            kpi_nl = f"{float(rk.rows[0][0]):.2f} €/MWh"
        except (TypeError, ValueError):
            kpi_nl = str(rk.rows[0][0])

    return html.Div(
        className="space-y-8",
        children=[
            html.Div(
                className="grid gap-4 sm:grid-cols-2",
                children=[
                    su.stat_card("Latest NL − DE-LU spread", kpi_nl, "Most recent hour — `demo_prices_spot_hourly`"),
                    su.stat_card("Curve type", "Hourly locational", "Aligned delivery hours, day-ahead product"),
                ],
            ),
            html.Div(
                className="grid gap-6 lg:grid-cols-2",
                children=[
                    html.Div(
                        className="chart-panel p-6",
                        children=[
                            dcc.Graph(figure=fig_nl, config={"displayModeBar": False}),
                            html.P(
                                "Positive means NL day-ahead above DE-LU for that hour — basis / congestion context (synthetic).",
                                className="mt-2 text-xs text-slate-500",
                            ),
                        ],
                    ),
                    html.Div(
                        className="chart-panel p-6",
                        children=[
                            dcc.Graph(figure=fig_fr, config={"displayModeBar": False}),
                            html.P(
                                "Second neighbour spread for regional comparison. Same source table as chart left.",
                                className="mt-2 text-xs text-slate-500",
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )
