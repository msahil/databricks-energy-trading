"""
Shared layout helpers for Capability 02 (Trade capture & pricing).

Widgets read `demo_trades_otc_remit_style`, `demo_consumer_contracts`, `demo_downstream_exports`
(see `modules/forecasting/features/02-trade-capture-and-pricing.md`).
"""

from __future__ import annotations

import plotly.graph_objects as go
from dash import html

import m01_common as m1
from uc_sql import SqlResult

CAP02_LABEL = "Trade capture & pricing"


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
        capability_label=CAP02_LABEL,
    )


def fig_bar_categories(
    labels: list[str],
    values: list[float],
    *,
    title: str,
    y_title: str,
    color: str = "#ff3621",
) -> go.Figure:
    fig = go.Figure(
        data=[
            go.Bar(
                x=labels,
                y=values,
                marker_color=color,
                text=[f"{v:,.0f}" if abs(v) >= 100 else f"{v:.2f}" for v in values],
                textposition="outside",
            )
        ]
    )
    fig.update_layout(
        title=dict(text=title, font=dict(size=14), x=0.02, xanchor="left"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=340,
        margin=dict(l=48, r=24, t=56, b=88),
        showlegend=False,
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor="#e2e8f0", title=y_title),
        font=dict(family="Inter, ui-sans-serif, system-ui, sans-serif", color="#475569", size=12),
    )
    return fig


def fig_pie_counts(labels: list[str], values: list[int], *, title: str) -> go.Figure:
    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.35,
                textinfo="label+percent",
                marker=dict(line=dict(color="#fff", width=1)),
            )
        ]
    )
    fig.update_layout(
        title=dict(text=title, font=dict(size=14), x=0.02, xanchor="left"),
        paper_bgcolor="rgba(0,0,0,0)",
        height=340,
        margin=dict(l=48, r=24, t=56, b=m1.CHART_MARGIN_BOTTOM_WITH_LEGEND),
        showlegend=True,
        legend=m1.legend_below_chart(),
        font=dict(family="Inter, ui-sans-serif, system-ui, sans-serif", color="#475569", size=12),
    )
    return fig


def fig_scatter_exec(
    xs: list,
    ys: list[float],
    names: list[str],
    *,
    title: str,
    y_title: str,
) -> go.Figure:
    from collections import defaultdict

    colors = ("#0f172a", "#ff3621", "#2563eb", "#059669", "#7c3aed")
    by_z: dict[str, tuple[list, list]] = defaultdict(lambda: ([], []))
    for x, y, zone in zip(xs, ys, names):
        if y is None:
            continue
        by_z[zone][0].append(x)
        by_z[zone][1].append(y)
    fig = go.Figure()
    for i, (zone, (xx, yy)) in enumerate(sorted(by_z.items())):
        fig.add_trace(
            go.Scatter(
                x=xx,
                y=yy,
                mode="markers",
                name=zone,
                marker=dict(size=8, color=colors[i % len(colors)]),
            )
        )
    fig.update_layout(
        title=dict(text=title, font=dict(size=14), x=0.02, xanchor="left"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=360,
        margin=dict(l=48, r=24, t=56, b=m1.CHART_MARGIN_BOTTOM_WITH_LEGEND),
        xaxis=m1.xaxis_title_grid("Execution time (UTC)"),
        yaxis=dict(showgrid=True, gridcolor="#e2e8f0", title=y_title),
        font=dict(family="Inter, ui-sans-serif, system-ui, sans-serif", color="#475569", size=12),
        legend=m1.legend_below_chart(),
    )
    return fig


def sql_table_limited(r: SqlResult, *, caption: str | None = None, max_rows: int = 25) -> html.Div:
    if not r.ok:
        return html.P(r.error or "Query failed", className="text-sm text-red-600")
    if not r.rows or not r.columns:
        return html.P("No rows.", className="text-sm text-slate-500")
    rows = r.rows[:max_rows]
    head = html.Tr(
        [
            html.Th(
                c,
                className="border-b border-slate-200 bg-slate-50 px-3 py-2 text-left text-xs font-semibold text-slate-700",
            )
            for c in r.columns
        ]
    )
    body = [
        html.Tr(
            [
                html.Td(str(c) if c is not None else "", className="border-b border-slate-100 px-3 py-1.5 text-xs text-slate-800")
                for c in row
            ]
        )
        for row in rows
    ]
    ch: list = [
        html.Div(
            className="w-full overflow-x-auto",
            children=[
                html.Table(
                    className="w-full min-w-[640px] border-collapse text-sm",
                    children=[html.Thead(head), html.Tbody(body)],
                )
            ],
        )
    ]
    if caption:
        ch.append(html.P(caption, className="mt-2 text-xs text-slate-500"))
    return html.Div(children=ch)
