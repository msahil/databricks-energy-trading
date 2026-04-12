"""
Shared layout and chart helpers for Capability 01 (Market data & visualisation) pages.

Chart helpers assume SQL rows are **newest-first**; they reverse to chronological order for plotting.
"""

from __future__ import annotations

from collections import defaultdict

import plotly.graph_objects as go
from dash import dcc, html

from uc_sql import SqlResult

_DEFAULT_MULTILINE_COLORS = ("#0f172a", "#ff3621", "#2563eb", "#059669", "#7c3aed", "#ea580c", "#0369a1")

# Extra bottom margin (px) so x-axis title + horizontal legend do not overlap.
CHART_MARGIN_BOTTOM_WITH_LEGEND = 132


# Legends above the plot (y > 1) overlap chart titles — keep legend below the x-axis.
def legend_below_chart() -> dict:
    return dict(
        orientation="h",
        yanchor="top",
        y=-0.38,
        x=0.5,
        xanchor="center",
        font=dict(size=11),
    )


def xaxis_title_grid(text: str) -> dict:
    """X-axis title with standoff so labels clear the legend band below the plot."""
    return dict(
        title=dict(text=text, standoff=16),
        showgrid=True,
        gridcolor="#e2e8f0",
    )


def _title_top_left() -> dict:
    return dict(x=0.02, xanchor="left", pad=dict(b=8))


CAP01_LABEL = "Market data & visualisation"


def select_warehouse_prompt() -> html.Div:
    return html.Div(
        className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900",
        children=dcc.Markdown(
            "**Choose a running warehouse** in the header to load the views.\n\n"
            "*Until you do, charts and tables stay empty.*",
            className="page-intro-markdown w-full min-w-0 !text-amber-900 [&_strong]:!text-amber-950",
        ),
    )


def page_shell(
    *,
    h1: str,
    blurb: str,
    content_id: str,
    footnote: str,
    capability_label: str = CAP01_LABEL,
) -> html.Main:
    return html.Main(
        className="w-full min-w-0 max-w-none flex-1 space-y-8 px-4 py-10 sm:px-6 lg:px-8",
        children=[
            html.Div(
                className="w-full min-w-0 space-y-3",
                children=[
                    html.P(capability_label, className="text-xs font-semibold uppercase tracking-wide text-[#ff3621]"),
                    html.H1(h1, className="text-2xl font-bold tracking-tight text-slate-900"),
                    dcc.Markdown(
                        blurb,
                        className="page-intro-markdown w-full min-w-0 text-sm leading-relaxed text-slate-600",
                    ),
                ],
            ),
            dcc.Loading(
                id=f"{content_id}-loading",
                type="circle",
                color="#ff3621",
                fullscreen=False,
                className="dash-loading-spinner-root",
                parent_className="loading-parent w-full",
                parent_style={
                    "position": "relative",
                    "minHeight": "12rem",
                    "width": "100%",
                },
                children=html.Div(id=content_id, className="w-full min-h-[12rem]", children=[]),
            ),
            html.P(footnote, className="text-xs text-slate-400"),
        ],
    )


def sql_html_table(r: SqlResult, *, caption: str | None = None) -> html.Div:
    if not r.ok:
        return html.P(r.error or "Query failed", className="text-sm text-red-600")
    if not r.rows or not r.columns:
        return html.P("No rows.", className="text-sm text-slate-500")
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
        for row in r.rows
    ]
    ch = [
        html.Table(className="w-full min-w-[480px] border-collapse text-sm", children=[html.Thead(head), html.Tbody(body)]),
    ]
    if caption:
        ch.append(html.P(caption, className="mt-2 text-xs text-slate-500"))
    return html.Div(children=ch)


def empty_fig(title: str, note: str) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text=note,
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.5,
        showarrow=False,
        font=dict(size=13, color="#64748b"),
    )
    fig.update_layout(
        title=dict(text=title, font=dict(size=14)),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=320,
        margin=dict(l=48, r=24, t=48, b=48),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        font=dict(family="Inter, ui-sans-serif, system-ui, sans-serif"),
    )
    return fig


def fig_prices(rows: list[list]) -> go.Figure:
    xs: list = []
    ys: list = []
    for r in reversed(rows):
        if len(r) >= 2:
            xs.append(r[0])
            ys.append(float(r[1]) if r[1] not in ("", None) else None)
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=xs,
            y=ys,
            mode="lines",
            name="series",
            line=dict(color="#ff3621", width=2),
        )
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=340,
        margin=dict(l=48, r=24, t=56, b=48),
        showlegend=False,
        xaxis=dict(showgrid=True, gridcolor="#e2e8f0"),
        yaxis=dict(showgrid=True, gridcolor="#e2e8f0"),
        font=dict(family="Inter, ui-sans-serif, system-ui, sans-serif", color="#475569", size=12),
    )
    return fig


def fig_fundamentals(rows: list[list]) -> go.Figure:
    xs: list = []
    load: list = []
    solar: list = []
    wind: list = []
    for r in reversed(rows):
        if len(r) >= 4:
            xs.append(r[0])
            try:
                load.append(float(r[1]) if r[1] not in ("", None) else None)
            except (TypeError, ValueError):
                load.append(None)
            try:
                solar.append(float(r[2]) if r[2] not in ("", None) else None)
            except (TypeError, ValueError):
                solar.append(None)
            try:
                wind.append(float(r[3]) if r[3] not in ("", None) else None)
            except (TypeError, ValueError):
                wind.append(None)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=xs, y=load, name="load_mw", line=dict(color="#0f172a", width=1.8)))
    fig.add_trace(go.Scatter(x=xs, y=solar, name="solar_mw_est", line=dict(color="#f59e0b", width=1.5)))
    fig.add_trace(go.Scatter(x=xs, y=wind, name="wind_ms", line=dict(color="#3b82f6", width=1.5), yaxis="y2"))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=340,
        margin=dict(l=48, r=56, t=56, b=CHART_MARGIN_BOTTOM_WITH_LEGEND),
        legend=legend_below_chart(),
        xaxis=xaxis_title_grid("ts"),
        yaxis=dict(title="MW", showgrid=True, gridcolor="#e2e8f0", side="left"),
        yaxis2=dict(title="m/s", overlaying="y", side="right", showgrid=False),
        font=dict(family="Inter, ui-sans-serif, system-ui, sans-serif", color="#475569", size=12),
    )
    return fig


def series_from_long_rows(
    rows: list[list],
    *,
    ts_col: int = 0,
    name_col: int = 1,
    val_col: int = 2,
) -> dict[str, list[tuple]]:
    """
    Pivot long-format SQL rows into {series_name: [(ts, value), ...]} sorted by timestamp.
    Skips non-numeric values.
    """
    buckets: dict[str, list[tuple]] = defaultdict(list)
    for r in rows:
        if len(r) <= max(ts_col, name_col, val_col):
            continue
        ts, name, raw = r[ts_col], r[name_col], r[val_col]
        try:
            v = float(raw) if raw not in ("", None) else None
        except (TypeError, ValueError):
            v = None
        if v is None:
            continue
        buckets[str(name)].append((ts, v))
    for pts in buckets.values():
        pts.sort(key=lambda x: x[0])
    return dict(buckets)


def fig_multiline_named(
    series: dict[str, list[tuple]],
    *,
    title: str,
    y_title: str,
    x_title: str = "",
    colors: tuple[str, ...] | None = None,
) -> go.Figure:
    """Plot multiple aligned time series (each list is (ts, y) sorted ascending)."""
    fig = go.Figure()
    palette = colors or _DEFAULT_MULTILINE_COLORS
    for i, (name, pts) in enumerate(sorted(series.items(), key=lambda kv: kv[0])):
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        fig.add_trace(
            go.Scatter(
                x=xs,
                y=ys,
                mode="lines",
                name=name,
                line=dict(color=palette[i % len(palette)], width=2),
            )
        )
    fig.update_layout(
        title=dict(text=title, font=dict(size=14), **_title_top_left()),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=380,
        margin=dict(l=56, r=32, t=72, b=CHART_MARGIN_BOTTOM_WITH_LEGEND),
        legend=legend_below_chart(),
        xaxis=xaxis_title_grid(x_title or ""),
        yaxis=dict(title=y_title, showgrid=True, gridcolor="#e2e8f0"),
        font=dict(family="Inter, ui-sans-serif, system-ui, sans-serif", color="#475569", size=12),
    )
    return fig


def fig_two_series(
    rows: list[list],
    *,
    name_a: str,
    name_b: str,
    title: str,
    y_title: str,
) -> go.Figure:
    """rows: delivery_ts, y1, y2 (aligned)."""
    xs: list = []
    y1s: list = []
    y2s: list = []
    for r in reversed(rows):
        if len(r) >= 3:
            xs.append(r[0])
            try:
                y1s.append(float(r[1]) if r[1] not in ("", None) else None)
            except (TypeError, ValueError):
                y1s.append(None)
            try:
                y2s.append(float(r[2]) if r[2] not in ("", None) else None)
            except (TypeError, ValueError):
                y2s.append(None)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=xs, y=y1s, name=name_a, line=dict(color="#ff3621", width=2)))
    fig.add_trace(go.Scatter(x=xs, y=y2s, mode="lines", name=name_b, line=dict(color="#2563eb", width=2)))
    fig.update_layout(
        title=dict(text=title, font=dict(size=14), **_title_top_left()),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=360,
        margin=dict(l=56, r=32, t=72, b=CHART_MARGIN_BOTTOM_WITH_LEGEND),
        legend=legend_below_chart(),
        xaxis=xaxis_title_grid(""),
        yaxis=dict(title=y_title, showgrid=True, gridcolor="#e2e8f0"),
        font=dict(family="Inter, ui-sans-serif, system-ui, sans-serif", color="#475569", size=12),
    )
    return fig
