"""
Shared layout pieces and demo charts (no Dash app instance — safe for pages/ imports).
"""

from __future__ import annotations

import statistics
import sys
from pathlib import Path

import plotly.graph_objects as go
from dash import dcc, html

import m01_common as m1


def _load_synth():
    dd = Path(__file__).resolve().parent.parent / "modules" / "forecasting" / "demo_data"
    if dd.is_dir() and (dd / "synthetic_generators.py").is_file():
        p = str(dd)
        if p not in sys.path:
            sys.path.insert(0, p)
        import synthetic_generators as synth

        return synth
    return None


def demo_figure() -> go.Figure:
    synth = _load_synth()
    if synth is not None:
        _x, da, roll = synth.chart_da_rolling_mean_eur_mwh(72, 24)
        hours = list(_x)
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=hours,
                y=da,
                mode="lines",
                name="DA (synth DE-LU)",
                line=dict(color="#ff3621", width=2.2),
            )
        )
        fig.add_trace(
            go.Scatter(
                x=hours,
                y=roll,
                mode="lines",
                name="24h rolling mean",
                line=dict(color="#64748b", width=1.8, dash="dash"),
            )
        )
        y_title = "€/MWh"
    else:
        hours = list(range(24))
        da = [62.0 + 14 * __import__("math").sin(h / 24 * 2 * __import__("math").pi) for h in hours]
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=hours,
                y=da,
                mode="lines",
                name="DA (fallback)",
                line=dict(color="#ff3621", width=2.2),
                fill="tozeroy",
                fillcolor="rgba(255, 54, 33, 0.12)",
            )
        )
        y_title = "€/MWh"
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=48, r=24, t=16, b=m1.CHART_MARGIN_BOTTOM_WITH_LEGEND),
        height=340,
        legend=m1.legend_below_chart(),
        xaxis={
            **m1.xaxis_title_grid("Hour index (from synthetic demo start)"),
            "zeroline": False,
        },
        yaxis=dict(
            title=y_title,
            showgrid=True,
            gridcolor="#e2e8f0",
            zeroline=False,
        ),
        font=dict(family="Inter, ui-sans-serif, system-ui, sans-serif", color="#475569", size=12),
    )
    return fig


def demo_stat_values() -> tuple[str, ...]:
    synth = _load_synth()
    if synth is None:
        return (
            "DE-LU DA (t)",
            "€—",
            "synth module not on path",
            "NL−DE-LU spread",
            "€—",
            "add forecasting/demo_data",
            "DA volatility σ",
            "€—",
            "add forecasting/demo_data",
        )
    _x, da, roll = synth.chart_da_rolling_mean_eur_mwh(168, 24)
    last = da[-1]
    tail = da[-24:]
    vol24 = statistics.pstdev(tail) if len(tail) > 1 else 0.0
    vol168 = statistics.pstdev(da) if len(da) > 1 else 0.0
    neg_hrs = sum(1 for v in da if v < 0)
    lo, hi = synth.nl_de_spread_range_eur_mwh(168)
    return (
        "DE-LU DA (last hr)",
        f"€{last:.2f}/MWh",
        f"{neg_hrs} neg. hrs · roll μ €{roll[-1]:.2f}",
        "NL−DE-LU DA spread (7d range)",
        f"€{lo:.2f} … €{hi:.2f}/MWh",
        "synthetic locational basis",
        "DA volatility σ",
        f"24h €{vol24:.2f} · 168h €{vol168:.2f}/MWh",
        "trailing vs full window · synthetic",
    )


FORECASTING_NAV_SECTIONS: tuple[tuple[str, tuple[tuple[str, str], ...]], ...] = (
    (
        "Market data & visualisation",
        (
            ("Overview", "/market-data"),
            ("Prices & derivatives", "/market-data/prices"),
            ("System & transparency", "/market-data/system"),
            ("Weather & commodities", "/market-data/weather"),
            ("Data quality & governance", "/market-data/governance"),
            ("Marks & curves", "/market-data/marks"),
            ("Analytics & ML", "/market-data/analytics"),
            ("Visualisation", "/market-data/visualisation"),
        ),
    ),
    (
        "Trade capture & pricing",
        (
            ("Overview", "/trade-capture"),
            ("Trades blotter", "/trade-capture/trades"),
            ("Pricing & exposure", "/trade-capture/pricing"),
            ("Regulatory & clearing", "/trade-capture/regulatory"),
            ("Contracts & downstream", "/trade-capture/lifecycle"),
        ),
    ),
    (
        "Forecasting & predictive analytics",
        (
            ("Overview", "/forecasting"),
            ("Fundamentals forecasting", "/forecasting/fundamentals"),
            ("Price & spread forecasting", "/forecasting/prices"),
            ("Benchmarking & evaluation", "/forecasting/benchmarks"),
            ("MLOps & governance", "/forecasting/mlops"),
        ),
    ),
    (
        "Strategy, optimisation & algo trading",
        (
            ("Overview", "/strategy"),
            ("Assisted strategy specification", "/strategy/spec"),
            ("Backtesting", "/strategy/backtest"),
            ("Portfolio & asset optimisation", "/strategy/optimisation"),
            ("Algorithmic & automated trading", "/strategy/algo"),
            ("Monitoring & incident", "/strategy/monitoring"),
        ),
    ),
)


def spec_anchor_strip() -> html.Div:
    sections_out: list = [
        html.P(
            "Capability map — see `modules/forecasting/features/input.md` and `01-*.md` … `04-*.md` (full §4.x specs).",
            className="mb-4 text-xs text-slate-500",
        ),
    ]
    for section_title, links in FORECASTING_NAV_SECTIONS:
        sections_out.append(
            html.H3(section_title, className="mb-2 mt-8 text-sm font-semibold text-slate-800 first:mt-0"),
        )
        for label, href in links:
            aid = href.removeprefix("#")
            sections_out.append(
                html.Div(
                    id=aid,
                    className="scroll-mt-28 border-b border-slate-100 py-5 last:border-b-0",
                    children=[html.P(label, className="text-sm leading-snug text-slate-600")],
                )
            )
    return html.Div(
        className="mt-10 border-t border-slate-200/80 pt-6",
        children=sections_out,
    )


def stat_card(title: str, value: str, hint: str) -> html.Div:
    return html.Div(
        className="card-elevated p-5",
        children=[
            html.P(title, className="text-xs font-medium uppercase tracking-wide text-slate-500"),
            html.P(value, className="mt-2 text-2xl font-semibold tracking-tight text-slate-900"),
            html.P(hint, className="mt-1 text-sm text-slate-500"),
        ],
    )


def nav_link(label: str, href: str) -> html.A | dcc.Link:
    cls = "nav-link-dbx block"
    if href.startswith("/"):
        return dcc.Link(label, href=href, className=cls)
    return html.A(label, href=href, className=cls)


def collapsible_nav_section(title: str, links: list[tuple[str, str]], *, default_open: bool = True) -> html.Details:
    return html.Details(
        className="border-b border-slate-200 last:border-b-0",
        open=default_open,
        children=[
            html.Summary(
                className=(
                    "flex cursor-pointer select-none items-center justify-between gap-2 py-2 pl-1 "
                    "pr-2 text-[13px] font-semibold leading-snug text-slate-800 transition"
                ),
                children=[
                    html.Span(title),
                    html.Span(
                        "▾",
                        className="nav-chevron inline-block text-xs text-slate-400 transition-transform duration-200",
                    ),
                ],
            ),
            html.Nav(
                className="nav-rail ml-1 space-y-0 pb-2 pl-3",
                children=[nav_link(label, href) for label, href in links],
            ),
        ],
    )


def sidebar(logo_url: str) -> html.Aside:
    return html.Aside(
        className="sidebar-shell flex h-screen w-[300px] shrink-0 flex-col",
        children=[
            html.Div(
                className="flex h-[60px] w-[300px] shrink-0 items-center overflow-hidden p-0",
                children=[
                    html.Img(
                        src=logo_url,
                        alt="Databricks",
                        className="block h-[60px] w-[300px] max-h-[60px] max-w-[300px] object-contain object-left",
                    ),
                ],
            ),
            html.Div(
                className="flex-1 overflow-y-auto border-t border-slate-200 px-3 py-2",
                children=[
                    *[
                        collapsible_nav_section(title, list(links), default_open=True)
                        for title, links in FORECASTING_NAV_SECTIONS
                    ],
                ],
            ),
        ],
    )
