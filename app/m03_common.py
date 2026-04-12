"""
Shared helpers for Capability 03 (Forecasting & predictive analytics).

Tables: `demo_forecasts_load_gen`, `demo_forecasts_market_prices`, `demo_carbon_spark_daily`,
`demo_backtest_metrics`, `demo_drift_metrics`, `demo_regime_labels`
(see `modules/forecasting/features/03-forecasting-and-predictive-analytics.md`).
"""

from __future__ import annotations

import plotly.graph_objects as go

import m01_common as m1
from dash import html

CAP03_LABEL = "Forecasting & predictive analytics"


def page_shell(
    *,
    h1: str,
    blurb: str,
    content_id: str,
    footnote: str,
) -> html.Main:
    return m1.page_shell(
        h1=h1,
        blurb=blurb,
        content_id=content_id,
        footnote=footnote,
        capability_label=CAP03_LABEL,
    )


def fig_load_gen_stack(rows: list[list]) -> go.Figure:
    """rows: ts, load_fcast_mw, wind_fcast_mw, solar_fcast_mw, residual_mw (newest-first ok)."""
    if not rows:
        return m1.empty_fig("Fundamentals forecasts", "No rows")
    xs: list = []
    load: list = []
    wind: list = []
    solar: list = []
    res: list = []
    for r in reversed(rows):
        if len(r) < 5:
            continue
        xs.append(r[0])
        try:
            load.append(float(r[1]) if r[1] not in ("", None) else None)
        except (TypeError, ValueError):
            load.append(None)
        try:
            wind.append(float(r[2]) if r[2] not in ("", None) else None)
        except (TypeError, ValueError):
            wind.append(None)
        try:
            solar.append(float(r[3]) if r[3] not in ("", None) else None)
        except (TypeError, ValueError):
            solar.append(None)
        try:
            res.append(float(r[4]) if r[4] not in ("", None) else None)
        except (TypeError, ValueError):
            res.append(None)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=xs, y=load, name="Load fcast", line=dict(color="#0f172a", width=2)))
    fig.add_trace(go.Scatter(x=xs, y=wind, name="Wind fcast", line=dict(color="#2563eb", width=2)))
    fig.add_trace(go.Scatter(x=xs, y=solar, name="Solar fcast", line=dict(color="#f59e0b", width=2)))
    fig.add_trace(go.Scatter(x=xs, y=res, name="Residual", line=dict(color="#ff3621", width=2, dash="dot")))
    fig.update_layout(
        title=dict(text="Fundamentals forecasts — load, renewables, residual", font=dict(size=14), x=0.02, xanchor="left"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=380,
        margin=dict(l=56, r=32, t=72, b=m1.CHART_MARGIN_BOTTOM_WITH_LEGEND),
        legend=m1.legend_below_chart(),
        xaxis=m1.xaxis_title_grid("Time"),
        yaxis=dict(title="MW", showgrid=True, gridcolor="#e2e8f0"),
        font=dict(family="Inter, ui-sans-serif, system-ui, sans-serif", color="#475569", size=12),
    )
    return fig


def fig_price_fan_da(rows: list[list]) -> go.Figure:
    """rows for single product EPEX_DA_HR: ts, mid, q10, q90 (chronological after reverse)."""
    if not rows:
        return m1.empty_fig("DA price fan", "No rows")
    xs: list = []
    mid: list = []
    q10: list = []
    q90: list = []
    for r in reversed(rows):
        if len(r) < 4:
            continue
        xs.append(r[0])
        for tgt, idx in ((mid, 1), (q10, 2), (q90, 3)):
            try:
                tgt.append(float(r[idx]) if r[idx] not in ("", None) else None)
            except (TypeError, ValueError):
                tgt.append(None)
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=xs + xs[::-1],
            y=q90 + q10[::-1],
            fill="toself",
            fillcolor="rgba(37, 99, 235, 0.15)",
            line=dict(color="rgba(255,255,255,0)"),
            name="q10–q90 band",
            hoverinfo="skip",
            showlegend=True,
        )
    )
    fig.add_trace(
        go.Scatter(x=xs, y=mid, name="Mid (€/MWh)", line=dict(color="#ff3621", width=2)),
    )
    fig.update_layout(
        title=dict(text="Day-ahead price forecast — mid with uncertainty band", font=dict(size=14), x=0.02, xanchor="left"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=380,
        margin=dict(l=56, r=32, t=72, b=m1.CHART_MARGIN_BOTTOM_WITH_LEGEND),
        legend=m1.legend_below_chart(),
        xaxis=m1.xaxis_title_grid("Time"),
        yaxis=dict(title="€/MWh", showgrid=True, gridcolor="#e2e8f0"),
        font=dict(family="Inter, ui-sans-serif, system-ui, sans-serif", color="#475569", size=12),
    )
    return fig


def fig_carbon_spark(rows: list[list]) -> go.Figure:
    """rows: ts, zone, eua_eur_t, goo_eur_mwh, ttf_eur_mwh, clean_spark_proxy (newest-first ok)."""
    if not rows:
        return m1.empty_fig("Carbon / spark", "No rows")
    xs: list = []
    eua: list = []
    ttf: list = []
    spark: list = []
    for r in reversed(rows):
        if len(r) < 5:
            continue
        xs.append(r[0])
        try:
            eua.append(float(r[2]) if r[2] not in ("", None) else None)
        except (TypeError, ValueError):
            eua.append(None)
        try:
            ttf.append(float(r[4]) if r[4] not in ("", None) else None)
        except (TypeError, ValueError):
            ttf.append(None)
        try:
            spark.append(float(r[5]) if r[5] not in ("", None) else None)
        except (TypeError, ValueError):
            spark.append(None)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=xs, y=eua, name="EUA €/t", line=dict(color="#059669", width=2)))
    fig.add_trace(go.Scatter(x=xs, y=ttf, name="TTF €/MWh", line=dict(color="#64748b", width=2)))
    fig.add_trace(go.Scatter(x=xs, y=spark, name="Clean spark proxy", line=dict(color="#ff3621", width=2.5)))
    fig.update_layout(
        title=dict(text="Carbon / spark-style daily analytics", font=dict(size=14), x=0.02, xanchor="left"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=360,
        margin=dict(l=56, r=32, t=72, b=m1.CHART_MARGIN_BOTTOM_WITH_LEGEND),
        legend=m1.legend_below_chart(),
        xaxis=m1.xaxis_title_grid("Date"),
        yaxis=dict(title="€ / composite", showgrid=True, gridcolor="#e2e8f0"),
        font=dict(family="Inter, ui-sans-serif, system-ui, sans-serif", color="#475569", size=12),
    )
    return fig


def fig_drift_psi(rows: list[list]) -> go.Figure:
    """rows: as_of_date, model_id, feature_group, zone, psi — build series per feature_group."""
    from collections import defaultdict

    by_fg: dict[str, list[tuple]] = defaultdict(list)
    for r in rows:
        if len(r) < 5:
            continue
        d, fg, psi = r[0], str(r[2]), r[4]
        try:
            pv = float(psi) if psi not in ("", None) else None
        except (TypeError, ValueError):
            pv = None
        if pv is None:
            continue
        by_fg[fg].append((d, pv))
    for pts in by_fg.values():
        pts.sort(key=lambda x: x[0])
    return m1.fig_multiline_named(
        dict(by_fg),
        title="Feature drift (PSI-style) by feature group",
        y_title="PSI",
        x_title="As-of date",
    )
