"""Lucide icon helpers for Dash layouts (module nav + capability heroes)."""

from __future__ import annotations

from dash import html

# Sidebar + capability page heroes — keep in sync per section.
OVERVIEW_NAV_ICONS: dict[str, str] = {
    "/": "home",
}

SHORT_TERM_NAV_ICONS: dict[str, str] = {
    "/short-term/overview": "layout-grid",
    "/short-term/control-tower": "layout-dashboard",
    "/short-term/near-delivery": "timer",
    "/short-term/dsr": "network",
    "/short-term/insights": "message-circle-question",
}

VOLUME_FORECAST_NAV_ICONS: dict[str, str] = {
    "/volume-forecasting/overview": "layout-grid",
    "/volume-forecasting/consumption-short-term": "gauge",
    "/volume-forecasting/consumption-long-term": "trending-up",
    "/volume-forecasting/industry": "factory",
    "/volume-forecasting/smart-metering": "plug-zap",
    "/volume-forecasting/wind": "wind",
    "/volume-forecasting/solar": "sun",
    "/volume-forecasting/publication": "send",
    "/volume-forecasting/accuracy": "target",
    "/volume-forecasting/insights": "message-circle-question",
}

_SECTION_NAV_ICONS: dict[str, dict[str, str]] = {
    "OVERVIEW": OVERVIEW_NAV_ICONS,
    "SHORT TERM TRADING": SHORT_TERM_NAV_ICONS,
    "VOLUME FORECASTING": VOLUME_FORECAST_NAV_ICONS,
}


def lucide(name: str, *, variant: str = "md") -> html.I:
    """Render a Lucide icon placeholder; ``dip_lucide.js`` replaces with SVG."""
    cls = {
        "sm": "ui-lucide ui-lucide-sm",
        "md": "ui-lucide",
        "nav": "nav-link-lucide",
        "hero": "curve-page-hero-lucide",
    }.get(variant, "ui-lucide")
    return html.I(className=cls, **{"data-lucide": name, "aria-hidden": "true"})


def hero_title(title: str, icon: str) -> html.Div:
    """Page hero title row with Lucide icon (short-term capability pages)."""
    return html.Div(
        className="curve-page-title-row",
        children=[
            lucide(icon, variant="hero"),
            html.H1(title, className="curve-page-title"),
        ],
    )


def section_nav_icon(href: str, *, section_title: str) -> str | None:
    return _SECTION_NAV_ICONS.get(section_title, {}).get(href)


def short_term_nav_icon(href: str, *, section_title: str) -> str | None:
    """Backward-compatible alias for short-term sidebar icons."""
    return section_nav_icon(href, section_title=section_title)
