"""Reusable slide content components and deck shell for presentation-style Dash pages."""

from __future__ import annotations

from dash import dcc, html


def slide_hl(text: str) -> html.Strong:
    return html.Strong(text, className="slide-hl")


def slide_points(items: tuple[tuple[str, str], ...], *, accent: bool = False) -> html.Ul:
    """Each item: (highlight phrase, supporting detail)."""
    cls = "slide-points" + (" slide-points-accent" if accent else "")
    return html.Ul(
        [
            html.Li(
                [
                    html.Strong(lead, className="slide-hl"),
                    html.Span(f" — {detail}", className="slide-point-detail"),
                ],
                className="slide-point",
            )
            for lead, detail in items
        ],
        className=cls,
    )


def slide_callout(title: str, body: str, *, accent: bool = False) -> html.Div:
    cls = "slide-callout" + (" slide-callout-accent" if accent else "")
    return html.Div(
        className=cls,
        children=[
            html.P(title, className="slide-callout-title"),
            html.P(body, className="slide-callout-body"),
        ],
    )


def slide_bullets(items: tuple[str, ...], *, accent: bool = False) -> html.Ul:
    cls = "slide-bullets" + (" slide-bullets-accent" if accent else "")
    return html.Ul([html.Li(item) for item in items], className=cls)


def slide_cards(cards: tuple[tuple[str, str, str], ...]) -> html.Div:
    """Each card: (title, subtitle, body)."""
    return html.Div(
        className="slide-card-grid",
        children=[
            html.Div(
                className="slide-card",
                children=[
                    html.H4(card[0], className="slide-card-title"),
                    html.P(card[1], className="slide-card-subtitle"),
                    html.P(card[2], className="slide-card-body"),
                ],
            )
            for card in cards
        ],
    )


def slide_cards_rich(cards: tuple[tuple[str, str, str, str], ...]) -> html.Div:
    """Each card: (title, tag, body, footer)."""
    return html.Div(
        className="slide-card-grid",
        children=[
            html.Div(
                className="slide-card slide-card-rich",
                children=[
                    html.Div(
                        className="slide-card-head",
                        children=[
                            html.H4(card[0], className="slide-card-title"),
                            html.Span(card[1], className="slide-card-tag"),
                        ],
                    ),
                    html.P(card[2], className="slide-card-body"),
                    html.P(card[3], className="slide-card-footer"),
                ],
            )
            for card in cards
        ],
    )


def slide_table_chips(tables: tuple[str, ...]) -> html.Div:
    return html.Div(
        className="slide-table-chips",
        children=[html.Code(t, className="slide-table-chip") for t in tables],
    )


def slide_stat_row(stats: tuple[tuple[str, str], ...]) -> html.Div:
    """Each stat: (big value, label)."""
    return html.Div(
        className="slide-stat-row",
        children=[
            html.Div(
                className="slide-stat",
                children=[
                    html.Span(value, className="slide-stat-value"),
                    html.Span(label, className="slide-stat-label"),
                ],
            )
            for value, label in stats
        ],
    )


def slide_formula(text: str) -> html.Pre:
    return html.Pre(text, className="slide-formula")


def slide_section_label(text: str) -> html.P:
    return html.P(text, className="slide-section-label")


def slide_pipeline(steps: tuple[tuple[str, str], ...]) -> html.Div:
    """Medallion / flow steps: (layer name, description)."""
    parts: list = []
    for i, (name, desc) in enumerate(steps):
        parts.append(
            html.Div(
                className="slide-pipeline-step",
                children=[
                    html.Span(name, className="slide-pipeline-name"),
                    html.Span(desc, className="slide-pipeline-desc"),
                ],
            )
        )
        if i < len(steps) - 1:
            parts.append(html.Span("→", className="slide-pipeline-arrow"))
    return html.Div(className="slide-pipeline", children=parts)


def slide_widget_list(items: tuple[tuple[str, str], ...]) -> html.Ul:
    """Planned Dash widgets: (widget name, source)."""
    return html.Ul(
        className="slide-widget-list",
        children=[
            html.Li(
                [html.Strong(w, className="slide-hl"), html.Span(f" — {src}", className="slide-point-detail")],
                className="slide-widget-item",
            )
            for w, src in items
        ],
    )


def slide_matrix(
    headers: tuple[str, ...],
    rows: tuple[tuple[str, ...], ...],
    *,
    compact: bool = False,
) -> html.Div:
    """Compact data table for hedge matrices, KPI grids, etc."""
    cls = "slide-matrix" + (" slide-matrix-compact" if compact else "")
    return html.Div(
        className=cls,
        children=[
            html.Table(
                children=[
                    html.Thead(html.Tr([html.Th(h) for h in headers])),
                    html.Tbody(
                        [html.Tr([html.Td(c) for c in row]) for row in rows],
                    ),
                ],
            ),
        ],
    )


def slide_two_col(
    left_title: str,
    left_items: tuple[tuple[str, str], ...],
    right_title: str,
    right_items: tuple[tuple[str, str], ...],
) -> html.Div:
    return html.Div(
        className="slide-two-col",
        children=[
            html.Div(
                className="slide-col",
                children=[
                    html.H4(left_title, className="slide-col-title"),
                    slide_points(left_items),
                ],
            ),
            html.Div(
                className="slide-col slide-col-accent",
                children=[
                    html.H4(right_title, className="slide-col-title"),
                    slide_points(right_items, accent=True),
                ],
            ),
        ],
    )


def slide_challenge_cards(cards: tuple[tuple[str, str, tuple[str, ...]], ...]) -> html.Div:
    """Each card: (title, tag, bullet points). Legacy flat card grid."""
    return html.Div(
        className="slide-card-grid slide-challenge-grid",
        children=[
            html.Div(
                className="slide-card slide-challenge-card",
                children=[
                    html.H4(title, className="slide-card-title"),
                    html.P(subtitle, className="slide-card-subtitle"),
                    slide_bullets(bullets),
                ],
            )
            for title, subtitle, bullets in cards
        ],
    )


def slide_challenges_compact(cards: tuple[tuple[str, str, tuple[str, ...]], ...]) -> html.Div:
    """Compact 2×2 challenge grid — same panel chrome as slide_capabilities_compact."""
    panels = []
    for index, (title, tag, bullets) in enumerate(cards, start=1):
        panels.append(
            html.Div(
                className="slide-cap-panel slide-challenge-panel",
                children=[
                    html.Span(f"{index:02d}", className="slide-cap-index"),
                    html.Div(
                        className="slide-cap-main",
                        children=[
                            html.Div(
                                className="slide-cap-head",
                                children=[
                                    html.H4(title, className="slide-cap-title"),
                                    html.Span(tag, className="slide-cap-tag"),
                                ],
                            ),
                        ],
                    ),
                    html.Div(
                        className="slide-challenge-points",
                        children=[slide_bullets(bullets)],
                    ),
                ],
            )
        )
    return html.Div(
        className="slide-capabilities slide-challenges-compact",
        children=[html.Div(className="slide-cap-grid", children=panels)],
    )


def _cap_flow(steps: tuple[tuple[str, str], ...]) -> html.Div:
    """Three-step capability flow for compact capability panels."""
    parts: list = []
    for i, (name, desc) in enumerate(steps):
        parts.append(
            html.Div(
                className="slide-cap-step",
                children=[
                    html.Span(name, className="slide-cap-step-name"),
                    html.Span(desc, className="slide-cap-step-desc"),
                ],
            )
        )
        if i < len(steps) - 1:
            parts.append(html.Span("›", className="slide-cap-step-arrow"))
    return html.Div(className="slide-cap-flow", children=parts)


def slide_capabilities_compact(
    items: tuple[tuple[str, str, str, tuple[tuple[str, str], ...], str], ...],
    *,
    start_index: int = 1,
) -> html.Div:
    """Compact 2×2 capability grid: (title, tag, summary, pipeline, key_output).

    `start_index` sets the corner number of the first panel — use it when a set of
    capabilities is split across multiple slides so the numbering stays continuous.
    """
    panels = []
    for index, (title, tag, summary, pipeline, key_output) in enumerate(items, start=start_index):
        outcome = key_output.removeprefix("Outcome: ").strip()
        panels.append(
            html.Div(
                className="slide-cap-panel",
                children=[
                    html.Span(f"{index:02d}", className="slide-cap-index"),
                    html.Div(
                        className="slide-cap-main",
                        children=[
                            html.Div(
                                className="slide-cap-head",
                                children=[
                                    html.H4(title, className="slide-cap-title"),
                                    html.Span(tag, className="slide-cap-tag"),
                                ],
                            ),
                            html.P(summary, className="slide-cap-summary"),
                        ],
                    ),
                    _cap_flow(pipeline),
                    html.Div(
                        className="slide-cap-outcome",
                        children=[
                            html.Span("Outcome", className="slide-cap-outcome-label"),
                            html.P(outcome, className="slide-cap-output"),
                        ],
                    ),
                ],
            )
        )
    return html.Div(className="slide-capabilities", children=[html.Div(className="slide-cap-grid", children=panels)])


def slide_problem_solution(
    problem_title: str,
    problems: tuple[tuple[str, str], ...],
    solution_cards: tuple[tuple[str, str, str, str], ...],
) -> html.Div:
    """Two-column slide: pain points left, rich solution cards right."""
    return html.Div(
        className="slide-split-rich",
        children=[
            html.Div(
                className="slide-col",
                children=[
                    html.H4(problem_title, className="slide-col-title"),
                    slide_points(problems),
                ],
            ),
            html.Div(
                className="slide-col slide-col-cards",
                children=[slide_cards_rich(solution_cards)],
            ),
        ],
    )


def slide_deck(
    deck_id: str,
    *,
    subtitle: str = "",
    slide_count: int = 1,
    initial_viewport: html.Div | None = None,
    initial_counter: str = "1 / 1",
    initial_dots: list | None = None,
) -> html.Div:
    """Presentation deck shell — prev/next navigation; page module drives updates via callback."""
    if initial_dots is None:
        initial_dots = [html.Span(className="slide-dot slide-dot-active")]

    at_start = slide_count <= 1
    prev_cls = "slide-deck-btn slide-deck-btn-disabled" if at_start else "slide-deck-btn"
    next_cls = "slide-deck-btn slide-deck-btn-disabled" if at_start else "slide-deck-btn"
    progress_width = f"{(1 / max(slide_count, 1)) * 100:.2f}%"

    return html.Div(
        className="slide-deck",
        children=[
            dcc.Store(id=f"{deck_id}-index", data=0),
            html.Div(
                className="slide-deck-header",
                children=[
                    html.Div(
                        className="slide-deck-meta",
                        children=[
                            html.Span(subtitle or "Solution overview", className="slide-deck-kicker"),
                            html.Span(initial_counter, id=f"{deck_id}-counter", className="slide-deck-counter"),
                        ],
                    ),
                    html.Div(
                        className="slide-deck-nav",
                        children=[
                            html.Button("‹", id=f"{deck_id}-prev", className=prev_cls, n_clicks=0),
                            html.Button("›", id=f"{deck_id}-next", className=next_cls, n_clicks=0),
                        ],
                    ),
                ],
            ),
            html.Div(
                id=f"{deck_id}-viewport",
                className="slide-deck-viewport",
                children=initial_viewport,
            ),
            html.Div(
                className="slide-deck-progress-track",
                children=[
                    html.Div(
                        id=f"{deck_id}-progress",
                        className="slide-deck-progress-fill",
                        style={"width": progress_width},
                    ),
                ],
            ),
            html.Div(className="slide-deck-dots", id=f"{deck_id}-dots", children=initial_dots),
        ],
    )


def slide_panel(
    title: str,
    subtitle: str,
    body: html.Div | list,
    *,
    body_class: str = "slide-body",
    subtitle_id: str | None = None,
) -> html.Div:
    subtitle_props: dict = {"className": "slide-subtitle"}
    if subtitle_id:
        subtitle_props["id"] = subtitle_id
    return html.Div(
        className="slide-panel-inner",
        children=[
            html.Header(
                className="slide-header",
                children=[
                    html.H2(title, className="slide-title"),
                    html.P(subtitle, **subtitle_props),
                ],
            ),
            html.Div(body, className=body_class),
        ],
    )
