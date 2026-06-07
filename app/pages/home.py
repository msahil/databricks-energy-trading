"""Landing page — executive capability overview."""

from __future__ import annotations

import dash
from dash import html

import ui_icons as uicons

dash.register_page(__name__, path="/", name="Home", title="Energy Trading System")

# icon, title, outcome (executive one-liner)
_SHORT_TERM_CAPABILITIES: tuple[tuple[str, str, str], ...] = (
    ("layout-grid", "Overview & Architecture", "End-to-end prompt-desk story on the lakehouse."),
    ("timer", "Trading near delivery", "Square renewable delta before gate close — cut imbalance cash-out."),
    ("layout-dashboard", "Control Tower", "Live balance, dispatch, outages, and shift P&L in one operations view."),
    ("network", "DSR & Market Access", "Monetise fleet flex on balancing markets and settle with owners."),
    ("message-circle-question", "Trader insights (Genie)", "Ask the desk in plain English — same governed gold tables."),
)

_VOLUME_FORECAST_CAPABILITIES: tuple[tuple[str, str, str], ...] = (
    ("layout-grid", "Overview & Architecture", "Forecasting desk narrative — volumes before prices move."),
    ("gauge", "Customer Consumption (ST)", "Weather-driven load for the next hours and days."),
    ("trending-up", "Customer Consumption (LT)", "Electrification-aware shapes for multi-year hedges."),
    ("factory", "Industry Involvement", "Large-site load and flexible MW that moves the zonal balance."),
    ("plug-zap", "Smart Metering", "Governed profiles from millions of meters — GDPR-aware."),
    ("wind", "Wind Forecasting", "Ensemble generation forecast — the portfolio's biggest swing."),
    ("sun", "Solar Forecasting", "Midday surplus, capture-price risk, and behind-the-meter PV."),
    ("send", "Publication & Net Volume", "One official net volume every desk trades against."),
    ("target", "Forecast Accuracy & Value", "Forecast error priced in euros — the business case for ML."),
    ("message-circle-question", "Renewables insights (Genie)", "Renewables book performance without SQL."),
)


def _capability_card(icon: str, title: str, outcome: str, *, variant: str) -> html.Div:
    extra = " landing-cap-card-genie" if "Genie" in title else ""
    return html.Div(
        className=f"landing-cap-card landing-cap-card-{variant}{extra}",
        children=[
            html.Div(className="landing-cap-icon-wrap", children=[uicons.lucide(icon, variant="md")]),
            html.Div(
                className="landing-cap-body",
                children=[
                    html.H3(title, className="landing-cap-title"),
                    html.P(outcome, className="landing-cap-outcome"),
                ],
            ),
        ],
    )


def _module_panel(
    *,
    icon: str,
    eyebrow: str,
    title: str,
    headline: str,
    capabilities: tuple[tuple[str, str, str], ...],
    variant: str,
) -> html.Section:
    return html.Section(
        className=f"landing-module landing-module-{variant}",
        children=[
            html.Div(
                className="landing-module-banner",
                children=[
                    html.Div(
                        className="landing-module-banner-icon",
                        children=[uicons.lucide(icon, variant="md")],
                    ),
                    html.Div(
                        className="landing-module-banner-text",
                        children=[
                            html.Span(eyebrow, className="landing-module-eyebrow"),
                            html.H2(title, className="landing-module-title"),
                            html.P(headline, className="landing-module-headline"),
                        ],
                    ),
                ],
            ),
            html.Div(
                className="landing-cap-grid",
                children=[
                    _capability_card(icon_name, cap_title, outcome, variant=variant)
                    for icon_name, cap_title, outcome in capabilities
                ],
            ),
        ],
    )


def layout() -> html.Div:
    return html.Div(
        className="page-home",
        children=[
            html.Div(
                className="landing-shell",
                children=[
                    html.Div(
                        className="landing-executive-banner",
                        children=[
                            html.Div(
                                className="landing-banner-copy",
                                children=[
                                    html.H1("Energy Trading", className="landing-banner-title"),
                                    html.P(
                                        "Two governed capabilities on one European portfolio — "
                                        "balance the book in real time, forecast the volumes that "
                                        "drive every decision.",
                                        className="landing-banner-tagline",
                                    ),
                                ],
                            ),
                            html.Div(
                                className="landing-banner-pillars",
                                children=[
                                    html.Div(
                                        className="landing-pillar landing-pillar-prompt",
                                        children=[
                                            html.Div(
                                                className="landing-pillar-icon",
                                                children=[uicons.lucide("zap", variant="md")],
                                            ),
                                            html.Div(
                                                className="landing-pillar-text",
                                                children=[
                                                    html.Span("Short-term trading", className="landing-pillar-label"),
                                                    html.Span(
                                                        "Prompt & spot desk — squaring, operations, flex, Genie",
                                                        className="landing-pillar-desc",
                                                    ),
                                                ],
                                            ),
                                        ],
                                    ),
                                    html.Div(
                                        className="landing-pillar landing-pillar-forecast",
                                        children=[
                                            html.Div(
                                                className="landing-pillar-icon",
                                                children=[uicons.lucide("activity", variant="md")],
                                            ),
                                            html.Div(
                                                className="landing-pillar-text",
                                                children=[
                                                    html.Span("Volume forecasting", className="landing-pillar-label"),
                                                    html.Span(
                                                        "Demand & renewables — publish, accuracy, Genie",
                                                        className="landing-pillar-desc",
                                                    ),
                                                ],
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                        ],
                    ),
                    html.Div(
                        className="landing-modules",
                        children=[
                            _module_panel(
                                icon="zap",
                                eyebrow="Prompt desk",
                                title="Short-term trading",
                                headline="From week-ahead to real time — physical balancing and asset optimisation on the prompt desk.",
                                capabilities=_SHORT_TERM_CAPABILITIES,
                                variant="prompt",
                            ),
                            _module_panel(
                                icon="activity",
                                eyebrow="Forecasting desk",
                                title="Volume forecasting",
                                headline="Credible megawatt forecasts at every horizon — one published net volume upstream of trading.",
                                capabilities=_VOLUME_FORECAST_CAPABILITIES,
                                variant="forecast",
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )
