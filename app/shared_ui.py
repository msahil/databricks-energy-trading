"""Shared navigation for the Energy Trading app."""

from __future__ import annotations

from dash import dcc, html

import ui_icons as icons

# Sidebar nav (see modules/*/specifications).
NAV_SECTIONS: tuple[tuple[str, tuple[tuple[str, str], ...]], ...] = (
    (
        "OVERVIEW",
        (("Home", "/"),),
    ),
    (
        "SHORT TERM TRADING",
        (
            ("Overview & Architecture", "/short-term/overview"),
            ("Control Tower", "/short-term/control-tower"),
            ("Trading near delivery", "/short-term/near-delivery"),
            ("DSR & Market Access", "/short-term/dsr"),
            ("Trader insights (Genie)", "/short-term/insights"),
        ),
    ),
    (
        "VOLUME FORECASTING",
        (
            ("Overview & Architecture", "/volume-forecasting/overview"),
            ("Customer Consumption (ST)", "/volume-forecasting/consumption-short-term"),
            ("Customer Consumption (LT)", "/volume-forecasting/consumption-long-term"),
            ("Industry Involvement", "/volume-forecasting/industry"),
            ("Smart Metering", "/volume-forecasting/smart-metering"),
            ("Wind Forecasting", "/volume-forecasting/wind"),
            ("Solar Forecasting", "/volume-forecasting/solar"),
            ("Publication & Net Volume", "/volume-forecasting/publication"),
            ("Forecast Accuracy & Value", "/volume-forecasting/accuracy"),
            ("Renewables insights (Genie)", "/volume-forecasting/insights"),
        ),
    ),
)


def nav_link(label: str, href: str, *, icon: str | None = None) -> dcc.Link:
    if icon:
        return dcc.Link(
            [icons.lucide(icon, variant="nav"), html.Span(label, className="nav-link-label")],
            href=href,
            className="nav-link-dbx nav-link-has-icon",
        )
    return dcc.Link(label, href=href, className="nav-link-dbx")


def collapsible_nav_section(title: str, links: list[tuple[str, str]], *, default_open: bool = True) -> html.Details:
    return html.Details(
        className="nav-section",
        open=default_open,
        children=[
            html.Summary(
                className="nav-section-header",
                children=[
                    html.Span(title, className="nav-section-title"),
                    html.Span("▾", className="nav-chevron"),
                ],
            ),
            html.Nav(
                className="nav-section-links",
                children=[
                    nav_link(label, href, icon=icons.section_nav_icon(href, section_title=title))
                    for label, href in links
                ],
            ),
        ],
    )


def sidebar(logo_url: str) -> html.Aside:
    return html.Aside(
        className="sidebar-shell flex h-screen w-[300px] shrink-0 flex-col",
        children=[
            html.Div(
                className="sidebar-brand flex h-[60px] w-full shrink-0 items-center overflow-hidden",
                children=[
                    html.Img(
                        src=logo_url,
                        alt="Databricks",
                        className="block h-[60px] w-full max-h-[60px] object-contain object-left",
                    ),
                ],
            ),
            html.Div(
                className="sidebar-nav-scroll flex-1 overflow-y-auto",
                children=[
                    html.Div(
                        className="sidebar-nav-sections",
                        children=[
                            collapsible_nav_section(title, list(links), default_open=True)
                            for title, links in NAV_SECTIONS
                        ],
                    ),
                ],
            ),
        ],
    )
