"""Reusable building blocks for progressive-reveal architecture diagrams."""

from __future__ import annotations

from dash import html


def dip_tile(icon: str, label: str) -> html.Div:
    return html.Div(
        className="dip-tile",
        children=[
            html.I(className="dip-lucide dip-lucide-xl", **{"data-lucide": icon}),
            html.Span(label, className="dip-tile-text"),
        ],
    )


def dip_foundation_tile(label: str) -> html.Div:
    return html.Div(
        className="dip-tile dip-tile-foundation",
        children=[html.Span(label, className="dip-tile-text")],
    )


def dip_block(title: str, items: tuple[tuple[str, str], ...], *, variant: str = "") -> html.Div:
    cls = "dip-block" + (f" dip-block-{variant}" if variant else "")
    return html.Div(
        className=cls,
        children=[
            html.Div(title, className="dip-block-title"),
            html.Div([dip_tile(icon, text) for icon, text in items], className="dip-block-grid"),
        ],
    )


def dip_segment(step: str, child: html.Div | list) -> html.Div:
    if not isinstance(child, list):
        child = [child]
    return html.Div(
        className=f"dip-arch-segment dip-arch-segment-{step}",
        children=child,
    )


def dip_medallion_row(
    title: str,
    layers: tuple[tuple[str, str, str], ...],
) -> html.Div:
    """Medallion panel: (tier class suffix, label, description) e.g. ('bronze', 'Bronze', '...')."""
    return html.Div(
        className="dip-models",
        children=[
            html.Div(title, className="dip-models-title"),
            html.Div(
                className="dip-medallion-row",
                children=[
                    html.Div(
                        className=f"dip-med dip-med-{tier}",
                        children=[html.Strong(label), html.Span(desc)],
                    )
                    for tier, label, desc in layers
                ],
            ),
        ],
    )


def dip_foundation_row(labels: tuple[str, ...]) -> html.Div:
    return html.Div(
        className="dip-foundation",
        children=[dip_foundation_tile(label) for label in labels],
    )


def dip_architecture_viewport(*children: html.Div | list) -> html.Div:
    """Top-level wrapper for a diagram grid."""
    return html.Div(
        className="dip-arch-viewport",
        children=[
            html.Div(className="dip-arch-grid", children=list(children)),
        ],
    )
