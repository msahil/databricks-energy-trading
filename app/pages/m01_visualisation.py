"""§4.7 — Visualisation (demo Delta)."""

from __future__ import annotations

import dash
from dash import Input, Output, callback, dcc, html
import plotly.graph_objects as go

import m01_common as m1
import uc_sql as uq

dash.register_page(
    __name__,
    path="/market-data/visualisation",
    name="M01 viz",
    title="Energy Trading — Curves & heatmaps",
    order=8,
)

_DOW_LABELS = ("Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat")

layout = m1.page_shell(
    h1="Visualisation",
    blurb="""Some risks are **shape** risks: prices are not flat through the week, and **hour-of-week** patterns drive **profile hedging**, **customer tariffs**, and **battery or demand-response** stories. This page combines a **heatmap** of average price by **hour and weekday** with **cross-border schedules**—nominated flows toward key neighbours—so you can **visualise** when the system is typically tight and how **interconnection** behaves in the same demo world.

Reach for it when you are explaining **peak/off-peak** structure to a non-trader, or when you want **chart-grade** visuals for **shape** and **border** topics alongside the raw series on **Prices**.

- **Weekly shape** — heatmap of average hourly prices by weekday to spot **morning peaks** and **weekend** effects.
- **Border context** — scheduled flows from Germany toward selected corridors to pair **price shape** with **nominated** import/export.
- **Risk angles** — supports narratives around **profile hedging**, **customer supply**, and **interconnection** limits.
- **Storytelling** — designed for **slides and briefings** where a single time series is not enough.
- **Coherence** — uses the same **hourly price** and **flow** demo tables documented in the footnote.

*Synthetic demo series—not operational schedule or real-time flow data.*
""",
    content_id="m01-viz-body",
    footnote="Sources: `demo_prices_spot_hourly`, `demo_cross_border_flows`.",
)


@callback(
    Output("m01-viz-body", "children"),
    Input("sql-warehouse-dropdown", "value"),
)
def _render(warehouse_id: str | None) -> html.Div:
    if not warehouse_id:
        return m1.select_warehouse_prompt()

    cat, sch = uq.default_catalog_schema()
    t_p = uq.full_table(cat, sch, "demo_prices_spot_hourly")
    t_x = uq.full_table(cat, sch, "demo_cross_border_flows")

    qh = f"""
        SELECT HOUR(delivery_ts) AS hod,
               CAST(DAYOFWEEK(delivery_ts) AS INT) AS dow,
               AVG(price_eur_mwh) AS avg_px
        FROM {t_p}
        WHERE bidding_zone = 'DE-LU' AND product_code = 'EPEX_DA_HR'
        GROUP BY HOUR(delivery_ts), DAYOFWEEK(delivery_ts)
    """
    rh = uq.run_sql(warehouse_id, qh, row_limit=500)

    fig_h = m1.empty_fig("Heatmap", rh.error or "No data")
    if rh.ok and rh.rows:
        from collections import defaultdict

        grid: dict[tuple[int, int], float] = defaultdict(float)
        for row in rh.rows:
            if len(row) >= 3:
                try:
                    h = int(float(row[0]))
                    d = int(float(row[1]))
                    grid[(h, d)] = float(row[2])
                except (TypeError, ValueError):
                    continue
        z = [[grid.get((h, d), None) for d in range(1, 8)] for h in range(24)]
        fig_h = go.Figure(
            data=go.Heatmap(
                z=z,
                colorscale="Reds",
                colorbar=dict(title="€/MWh"),
                x=[_DOW_LABELS[i] for i in range(7)],
                y=list(range(24)),
            )
        )
        fig_h.update_layout(
            title=dict(
                text="When prices are high or low — hour vs weekday (DE-LU day-ahead)",
                font=dict(size=14),
                x=0.02,
                xanchor="left",
            ),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=440,
            margin=dict(l=56, r=88, t=64, b=56),
            xaxis=dict(title="Weekday (1 = Sunday … 7 = Saturday)", side="bottom"),
            yaxis=dict(title="Hour of day", autorange="reversed"),
            font=dict(family="Inter, ui-sans-serif, system-ui, sans-serif", size=12, color="#475569"),
        )

    qf = f"""
        SELECT ts, from_country, to_country, mw
        FROM {t_x}
        WHERE from_country = 'DE' AND to_country IN ('NL', 'FR', 'PL')
        ORDER BY ts DESC
        LIMIT 504
    """
    rf = uq.run_sql(warehouse_id, qf, row_limit=600)
    fig_f = m1.empty_fig("Cross-border flows", rf.error or "No data")
    if rf.ok and rf.rows:
        ser = m1.series_from_long_rows(
            [[r[0], f"{r[1]}→{r[2]}", r[3]] for r in rf.rows],
            ts_col=0,
            name_col=1,
            val_col=2,
        )
        fig_f = m1.fig_multiline_named(
            ser,
            title="Cross-border energy — Germany toward neighbours",
            y_title="MW",
            x_title="Time",
        )

    return html.Div(
        className="space-y-8",
        children=[
            html.Div(
                className="chart-panel p-6",
                children=[
                    dcc.Graph(figure=fig_h, config={"displayModeBar": False}),
                    html.P(
                        "Average day-ahead price by clock hour and weekday (synthetic). `demo_prices_spot_hourly` — Sunday = 1 in engine.",
                        className="mt-2 text-xs text-slate-500",
                    ),
                ],
            ),
            html.Div(
                className="chart-panel p-6",
                children=[
                    dcc.Graph(figure=fig_f, config={"displayModeBar": False}),
                    html.P(
                        "Scheduled flows on key corridors; sign convention per synthetic dataset. `demo_cross_border_flows`.",
                        className="mt-2 text-xs text-slate-500",
                    ),
                ],
            ),
        ],
    )
