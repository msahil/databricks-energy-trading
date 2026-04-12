"""§4.3 — Ingestion: weather & commodities (demo Delta)."""

from __future__ import annotations

import dash
from dash import Input, Output, callback, dcc, html
import plotly.graph_objects as go

import m01_common as m1
import uc_sql as uq

dash.register_page(
    __name__,
    path="/market-data/weather",
    name="M01 weather",
    title="Energy Trading — Weather & commodities",
    order=4,
)

layout = m1.page_shell(
    h1="Weather & commodities",
    blurb="""Origination, risk, and analytics teams rarely look at power in isolation: **weather** drives load and renewables, **gas** sets the fuel cost for marginal plants, and **EU carbon** shifts the **thermal margin** for coal and gas. This page lines up those inputs in one place so you can explain **why** forward curves or spot might be repricing, and how a **cold spell**, **low wind**, or a **carbon spike** would show up in a desk narrative.

Use it when you are building a **fundamentals story** for a meeting, stress-testing a **hedge**, or connecting **NWP-style** drivers to the same demo fundamentals used elsewhere in the app.

- **Weather drivers** — temperature, wind, and solar radiation proxies at a representative point for load and RES views.
- **Gas benchmark** — European hub-style gas level to support fuel-switch and margin conversations.
- **Carbon** — allowance price level for EU ETS exposure in thermal margin bridges.
- **Cross-commodity** — one view to tie **power, gas, and carbon** without jumping between unrelated screens.
- **Consistency** — same synthetic demo series as other capability 01 pages so stories stay coherent.

*Demo data only—not live vendor, NWP, or exchange feeds.*
""",
    content_id="m01-weather-body",
    footnote=(
        "Sources: `demo_nwp_ecmwf_surface_style`, `demo_gas_hub_ttf_style`, `demo_eua_ets_daily_style`."
    ),
)


@callback(
    Output("m01-weather-body", "children"),
    Input("sql-warehouse-dropdown", "value"),
)
def _render(warehouse_id: str | None) -> html.Div:
    if not warehouse_id:
        return m1.select_warehouse_prompt()

    cat, sch = uq.default_catalog_schema()
    tn = uq.full_table(cat, sch, "demo_nwp_ecmwf_surface_style")
    tt = uq.full_table(cat, sch, "demo_gas_hub_ttf_style")
    te = uq.full_table(cat, sch, "demo_eua_ets_daily_style")

    qn = f"""
        SELECT valid_ts_utc, t2m_celsius, wind100_ms, ssrd_wm2
        FROM {tn}
        ORDER BY valid_ts_utc DESC
        LIMIT 168
    """
    rn = uq.run_sql(warehouse_id, qn, row_limit=500)
    fig_n = m1.empty_fig("NWP-style", rn.error or "No data")
    fig_ssrd = m1.empty_fig("SSRD", rn.error or "No data")
    if rn.ok and rn.rows:
        xs: list = []
        t2: list = []
        w1: list = []
        ssrd: list = []
        for row in reversed(rn.rows):
            if len(row) >= 4:
                xs.append(row[0])
                try:
                    t2.append(float(row[1]) if row[1] not in ("", None) else None)
                except (TypeError, ValueError):
                    t2.append(None)
                try:
                    w1.append(float(row[2]) if row[2] not in ("", None) else None)
                except (TypeError, ValueError):
                    w1.append(None)
                try:
                    ssrd.append(float(row[3]) if row[3] not in ("", None) else None)
                except (TypeError, ValueError):
                    ssrd.append(None)
        fig_n = go.Figure()
        fig_n.add_trace(go.Scatter(x=xs, y=t2, name="t2m °C", line=dict(color="#ea580c")))
        fig_n.add_trace(go.Scatter(x=xs, y=w1, name="wind @100m (m/s)", line=dict(color="#0284c7"), yaxis="y2"))
        fig_n.update_layout(
            title=dict(
                text="Weather drivers — temperature and wind (NWP-style demo)",
                font=dict(size=14),
                x=0.02,
                xanchor="left",
            ),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=340,
            margin=dict(l=48, r=56, t=64, b=m1.CHART_MARGIN_BOTTOM_WITH_LEGEND),
            legend=m1.legend_below_chart(),
            xaxis=m1.xaxis_title_grid("valid_ts_utc"),
            yaxis=dict(title="°C", showgrid=True, gridcolor="#e2e8f0"),
            yaxis2=dict(title="m/s", overlaying="y", side="right", showgrid=False),
            font=dict(family="Inter, ui-sans-serif, system-ui, sans-serif", size=12, color="#475569"),
        )
        fig_ssrd = go.Figure()
        fig_ssrd.add_trace(
            go.Scatter(x=xs, y=ssrd, name="SSRD", line=dict(color="#ca8a04", width=2), fill="tozeroy", fillcolor="rgba(202, 138, 4, 0.15)")
        )
        fig_ssrd.update_layout(
            title=dict(
                text="Solar radiation — driver for PV-style output (demo)",
                font=dict(size=14),
                x=0.02,
                xanchor="left",
            ),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=300,
            margin=dict(l=48, r=24, t=56, b=48),
            yaxis=dict(title="W/m²", showgrid=True, gridcolor="#e2e8f0"),
            xaxis=dict(title="valid_ts_utc", showgrid=True, gridcolor="#e2e8f0"),
            showlegend=False,
            font=dict(family="Inter, ui-sans-serif, system-ui, sans-serif", size=12, color="#475569"),
        )

    qt = f"""
        SELECT gas_day_date, hub_id, price, unit
        FROM {tt}
        ORDER BY gas_day_date ASC
        LIMIT 120
    """
    rt = uq.run_sql(warehouse_id, qt, row_limit=200)
    fig_t = m1.empty_fig("TTF gas", rt.error or "No data")
    if rt.ok and rt.rows:
        xs = [r[0] for r in rt.rows]
        ys = []
        for r in rt.rows:
            try:
                ys.append(float(r[2]) if r[2] not in ("", None) else None)
            except (TypeError, ValueError):
                ys.append(None)
        fig_t = go.Figure()
        fig_t.add_trace(
            go.Scatter(
                x=xs,
                y=ys,
                mode="lines",
                name="TTF DA",
                line=dict(color="#0e7490", width=2),
            )
        )
        fig_t.update_layout(
            title=dict(
                text="TTF — day-ahead gas benchmark (demo hub)",
                font=dict(size=14),
                x=0.02,
                xanchor="left",
            ),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=300,
            margin=dict(l=48, r=24, t=56, b=48),
            showlegend=False,
            yaxis=dict(title="EUR/MWh", showgrid=True, gridcolor="#e2e8f0"),
            xaxis=dict(title="gas_day_date", showgrid=True, gridcolor="#e2e8f0"),
            font=dict(family="Inter, ui-sans-serif, system-ui, sans-serif", size=12, color="#475569"),
        )

    qe = f"""
        SELECT business_date, settle_eur_tco2, contract_id_sim
        FROM {te}
        ORDER BY business_date ASC
        LIMIT 120
    """
    re = uq.run_sql(warehouse_id, qe, row_limit=200)
    fig_e = m1.empty_fig("EU ETS style", re.error or "No data")
    if re.ok and re.rows:
        xs = [r[0] for r in re.rows]
        ys = []
        for r in re.rows:
            try:
                ys.append(float(r[1]) if r[1] not in ("", None) else None)
            except (TypeError, ValueError):
                ys.append(None)
        fig_e = go.Figure()
        fig_e.add_trace(go.Scatter(x=xs, y=ys, mode="lines", line=dict(color="#15803d", width=2), name="EUA settle"))
        fig_e.update_layout(
            title=dict(
                text="EU ETS — allowance price (daily, demo)",
                font=dict(size=14),
                x=0.02,
                xanchor="left",
            ),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=300,
            margin=dict(l=48, r=24, t=56, b=48),
            showlegend=False,
            yaxis=dict(title="EUR/tCO2", showgrid=True, gridcolor="#e2e8f0"),
            xaxis=dict(title="business_date", showgrid=True, gridcolor="#e2e8f0"),
            font=dict(family="Inter, ui-sans-serif, system-ui, sans-serif", size=12, color="#475569"),
        )

    q_meta = f"""
        SELECT model_run_ts_utc, model_id_simulated, zone_label, lat, lon
        FROM {tn}
        ORDER BY valid_ts_utc DESC
        LIMIT 1
    """
    rmeta = uq.run_sql(warehouse_id, q_meta, row_limit=5)

    return html.Div(
        className="space-y-8",
        children=[
            html.Div(
                className="space-y-6",
                children=[
                    html.Div(
                        className="chart-panel p-6",
                        children=[
                            dcc.Graph(figure=fig_n, config={"displayModeBar": False}),
                            html.P(
                                "Temperature and wind for power demand & RES models. `demo_nwp_ecmwf_surface_style`.",
                                className="mt-2 text-xs text-slate-500",
                            ),
                        ],
                    ),
                    html.Div(
                        className="chart-panel p-6",
                        children=[
                            dcc.Graph(figure=fig_ssrd, config={"displayModeBar": False}),
                            html.P(
                                "Surface solar radiation for solar generation context. Same valid times as chart above.",
                                className="mt-2 text-xs text-slate-500",
                            ),
                        ],
                    ),
                    html.Div(
                        className="card-elevated overflow-x-auto p-4",
                        children=[
                            html.H2("Model run metadata (latest point)", className="mb-3 text-sm font-semibold text-slate-900"),
                            m1.sql_html_table(
                                rmeta,
                                caption="Run time, model label, coordinates — `demo_nwp_ecmwf_surface_style`.",
                            ),
                        ],
                    ),
                ],
            ),
            html.Div(
                className="grid gap-6 lg:grid-cols-2",
                children=[
                    html.Div(
                        className="chart-panel p-6",
                        children=[
                            dcc.Graph(figure=fig_t, config={"displayModeBar": False}),
                            html.P(
                                "European gas benchmark for spark / dark spread context. `demo_gas_hub_ttf_style`.",
                                className="mt-2 text-xs text-slate-500",
                            ),
                        ],
                    ),
                    html.Div(
                        className="chart-panel p-6",
                        children=[
                            dcc.Graph(figure=fig_e, config={"displayModeBar": False}),
                            html.P(
                                "Carbon price input for thermal assets. `demo_eua_ets_daily_style`.",
                                className="mt-2 text-xs text-slate-500",
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )
