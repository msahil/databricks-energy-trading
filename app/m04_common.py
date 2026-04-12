"""
Capability 04 — Strategy, optimisation & algorithmic trading.

Tables from `04_strategy_optimisation_and_algo_trading.ipynb`; see
`modules/forecasting/features/04-strategy-optimisation-and-algorithmic-trading.md`.
"""

from __future__ import annotations

import plotly.graph_objects as go

import m01_common as m1
from dash import html

CAP04_LABEL = "Strategy, optimisation & algo trading"


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
        capability_label=CAP04_LABEL,
    )


def fig_forecast_vs_actual(rows: list[list]) -> go.Figure:
    """rows: ts, forecast_eur_mwh, actual_eur_mwh (newest-first ok)."""
    if not rows:
        return m1.empty_fig("Forecast vs actual", "No rows")
    return m1.fig_two_series(
        [[r[0], r[1], r[2]] for r in rows],
        name_a="Forecast €/MWh",
        name_b="Actual €/MWh",
        title="Forecast vs actual — DA-style product (DE-LU)",
        y_title="€/MWh",
    )


def fig_error_series(rows: list[list]) -> go.Figure:
    """rows: ts, error_eur_mwh (chronological after processing)."""
    if not rows:
        return m1.empty_fig("Forecast error", "No rows")
    xs: list = []
    ys: list = []
    for r in reversed(rows):
        if len(r) < 2:
            continue
        xs.append(r[0])
        try:
            ys.append(float(r[1]) if r[1] not in ("", None) else None)
        except (TypeError, ValueError):
            ys.append(None)
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=xs,
            y=ys,
            mode="lines",
            name="Error (actual − forecast)",
            line=dict(color="#ff3621", width=2),
            fill="tozeroy",
            fillcolor="rgba(255, 54, 33, 0.12)",
        )
    )
    fig.update_layout(
        title=dict(text="Hourly forecast error", font=dict(size=14), x=0.02, xanchor="left"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=320,
        margin=dict(l=56, r=32, t=56, b=88),
        showlegend=False,
        xaxis=dict(showgrid=True, gridcolor="#e2e8f0", title="Time"),
        yaxis=dict(title="€/MWh", showgrid=True, gridcolor="#e2e8f0"),
        font=dict(family="Inter, ui-sans-serif, system-ui, sans-serif", color="#475569", size=12),
    )
    return fig
