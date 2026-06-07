"""
Trader insights (Genie) — short-term natural-language analytics launcher.
Spec: modules/short-term/specifications/04-trader-insights-genie.md
"""

from __future__ import annotations

import dash
from dash import Input, Output, State, callback, dcc, html

import genie_spaces as gs
import uc_pages as ucp
import ui_icons as uicons

dash.register_page(
    __name__,
    path="/short-term/insights",
    name="Trader insights (Genie)",
    title="Trader insights (Genie) — Short-term trading",
)

_PAGE_TITLE = "Trader insights (Genie)"
_PAGE_SUMMARY = (
    "Ask plain-English questions over the same governed near-delivery, control-tower, and DSR tables "
    "the prompt desk already uses — without writing SQL. Choose a Genie Space below to read its "
    "description and sample prompts, then open it in the workspace with Agent mode enabled."
)

_GENIE_CALLOUT_TITLE = "Plain-English answers on the prompt desk"
_GENIE_CALLOUT_BODY = (
    "Before gate close or a shift handover, traders need squaring position, imbalance exposure, "
    "fleet flex, and REMIT context — without waiting on a quant. Genie lets you ask in everyday "
    "language: how much volume is still open, which intervals are closing, what the control tower "
    "balance looks like, or how much the VPP captured on negative-price absorb. Answers pull from "
    "the same short_term_* gold tables as the Dash capability pages, so squaring, operations, and "
    "aggregation desks share one story."
)

# App page only — Genie Space still has the full set from notebook 04.
_APP_DISPLAY_QUESTIONS: tuple[str, ...] = (
    "What is the net open position and projected cash-out on the latest delivery date?",
    "Which intervals still have OPEN gate status and a recommended squaring action in DE?",
    "What is the control-tower balance state and P&L since shift start?",
    "How much flex up and flex down is available in the DSR fleet today?",
    "Show verified DSR dispatch events triggered by negative prices or scarcity.",
)

_PRESENTER_LEAD = (
    f"{ucp.PRESENTER_LEAD_GENIE} Walk near-delivery → control tower → DSR first, then open Genie here."
)

_PRESENTER_SECTIONS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "1 — Pain point for traders",
        (
            "A trader mid-gate should be able to ask \"how exposed are we into the next close?\" and get a straight answer. "
            "Instead the truth is split across squaring, operations, outage feeds, and VPP screens — and the clock does "
            "not wait while someone opens five tabs or files a quant ticket.",
            "Shift handover suffers the same fragmentation: the outgoing trader knows the story in their head, but the "
            "incoming trader cannot query it in plain language against the same numbers everyone already uses for "
            "nominations and imbalance.",
            "Experienced desks are rightly skeptical of conversational AI. They assume it is a shadow copy of the market "
            "or a generic LLM hallucination. They will challenge any figure that does not trace to the governed tables "
            "they already saw on the structured dashboards.",
        ),
    ),
    (
        "2 — Business problem this solves",
        (
            "Genie answers in everyday language against the same short-term trading tables that power near-delivery "
            "squaring, the control tower balance view, REMIT events, and VPP dispatch — not a separate spreadsheet or "
            "a black-box chatbot trained on the internet.",
            "The trading copilot on the control tower proposes one curated play for the moment; Genie handles the "
            "follow-up question the room throws at you when curiosity beats the script — \"what if we only look at "
            "Germany?\" or \"show me verified flex since midday.\"",
            "Recommended demo order: near-delivery, then control tower, then DSR, then this page. Read a KPI aloud on "
            "a dashboard, then say \"watch me ask Genie the same thing in one sentence\" and click the matching sample "
            "tile. Traders nod when the numbers align. If someone challenges a figure, open the answer in the workspace "
            "and show SQL lineage — trust beats magic.",
        ),
    ),
    (
        "3 — This page and each widget",
        (
            "Page title and summary: Trader Insights — position this as conversational access to the short-term trading "
            "demo space. You are not replacing the dashboards; you are showing how a busy desk asks ad-hoc questions "
            "without waiting on an analyst.",
            "Page callout (accent box under the title): Read it before you touch Genie if the audience has not seen the "
            "other short-term pages. It frames squaring, operations, and aggregation as one desk story. If you already "
            "walked those screens, shorten the callout and move straight to Genie.",
            "Genie space dropdown: Say plainly, \"We pick the short-term trading space from this dropdown so questions "
            "stay on the prompt desk demo.\" Check the status line underneath — you want to see that a space is "
            "available before you promise a live answer. If the list is empty, refresh once; you do not need to "
            "troubleshoot aloud.",
            "Space description panel: Read the description paragraph — it tells the trader what kinds of questions this "
            "space is meant to handle. When you click Open in workspace, say you are moving to the chat experience "
            "traders would use in anger during a busy gate window.",
            "Sample question tiles: Introduce these as starter prompts a new user can click instead of typing — squaring "
            "position, balance state, critical outages, VPP dispatch. Pick the tile that matches what the room already "
            "cared about on the prior pages. In Genie, enable conversational agent mode if your workspace has it.",
            "Running the demo: Before you click, take one breath and restate the question in trader language — it models "
            "how they should think about Genie. Keep the same delivery day in your head as the pages you showed; if your "
            "question says \"today,\" it should match the trade date you picked earlier.",
            "Honest disclaimer: Remind the room these are illustrative demo figures, not live exchange or TSO feeds. "
            "That honesty builds credibility with experienced traders more than overselling realism.",
            "Close with conviction: \"Three structured desk views give discipline and speed — Genie gives you the "
            "cross-cutting question you did not know you needed to ask before the gate shuts.\"",
        ),
    ),
)


def _genie_callout() -> html.Div:
    return html.Div(
        className="ppa-ml-callout insights-genie-callout",
        children=[
            html.Div(
                className="ppa-ml-callout-head",
                children=[
                    html.Span(
                        className="ppa-ml-callout-icon",
                        children=[html.Span("AI", className="ppa-ml-callout-icon-text")],
                        **{"aria-hidden": "true"},
                    ),
                    html.Span(_GENIE_CALLOUT_TITLE, className="ppa-ml-callout-title"),
                ],
            ),
            html.P(_GENIE_CALLOUT_BODY, className="ppa-ml-callout-body"),
        ],
    )


def _page_header() -> html.Header:
    return html.Header(
        className="curve-page-hero",
        children=[
            html.Div(
                className="curve-page-hero-head",
                children=[
                    html.Div(
                        className="curve-page-hero-top",
                        children=[
                            html.Span("Short-term trading", className="curve-page-eyebrow"),
                            html.Span("Genie", className="curve-page-badge curve-page-badge-ml"),
                            html.Span("Natural language", className="curve-page-badge"),
                        ],
                    ),
                    ucp.presenter_tip_button("st-insights-presenter-tip-btn"),
                ],
            ),
            uicons.hero_title(_PAGE_TITLE, uicons.SHORT_TERM_NAV_ICONS["/short-term/insights"]),
            html.P(_PAGE_SUMMARY, className="curve-page-summary"),
            _genie_callout(),
        ],
    )


def _alert(message: str, *, kind: str = "warn") -> html.Div:
    cls = "curve-alert curve-alert-warn" if kind == "warn" else "curve-alert curve-alert-error"
    return html.Div(className=cls, children=[html.P(message)])


def _questions_for_app_page(api_questions: tuple[str, ...]) -> tuple[str, ...]:
    """Pick five demo questions for this page; does not change the Genie Space config."""
    if not api_questions:
        return _APP_DISPLAY_QUESTIONS
    by_text = {q.strip(): q for q in api_questions}
    return tuple(by_text.get(q.strip(), q) for q in _APP_DISPLAY_QUESTIONS)


def _sample_questions_panel(prompts: tuple[str, ...], *, from_api: bool) -> html.Div:
    lead = (
        "Starter questions for the demo (squaring, control tower, DSR). In Genie, turn on Agent mode and pick a tile—or ask your own."
        if from_api
        else "Showing default demo questions (could not load from the space)."
    )
    cards = [
        html.Div(
            className="insights-prompt-card",
            role="listitem",
            children=[
                html.Span(str(i), className="insights-prompt-index", **{"aria-hidden": "true"}),
                html.P(q, className="insights-prompt-text"),
            ],
        )
        for i, q in enumerate(prompts, 1)
    ]
    return html.Div(
        className="insights-space-prompts",
        children=[
            html.H3("Sample questions", className="insights-space-subtitle"),
            html.P(lead, className="insights-prompt-lead"),
            html.Div(className="insights-prompt-grid", role="list", children=cards),
        ],
    )


def _render_space_detail(space_id: str | None) -> html.Div:
    if not space_id:
        return html.Div(
            className="insights-space-detail insights-space-detail-empty",
            children=[html.P("Select a Genie Space to view its description and sample questions.", className="curve-section-lead")],
        )

    detail = gs.get_genie_space_detail(space_id)
    if detail.error:
        return _alert(f"Could not load Genie space: {detail.error}", kind="error")

    children: list = []
    if detail.workspace_url:
        children.append(
            html.P(
                [
                    html.A(
                        "Open Genie Space",
                        href=detail.workspace_url,
                        target="_blank",
                        rel="noopener noreferrer",
                        className="insights-genie-link",
                    ),
                    " — enable Agent mode, then use the sample question tiles.",
                ],
                className="curve-section-lead",
            )
        )

    if detail.description:
        children.append(
            html.Div(
                className="insights-space-description",
                children=[
                    html.H3("Description", className="insights-space-subtitle"),
                    dcc.Markdown(detail.description, className="insights-space-markdown"),
                ],
            )
        )
    else:
        children.append(html.P("No description on this space.", className="curve-section-lead"))

    prompts = _questions_for_app_page(detail.sample_questions)
    children.append(
        _sample_questions_panel(prompts, from_api=bool(detail.sample_questions)),
    )

    return html.Div(className="insights-space-detail", children=children)


def _insights_body() -> html.Div:
    return html.Div(
        className="curve-page-body insights-page-body",
        children=[
            html.Div(
                className="curve-section-card",
                children=[
                    html.H2("Genie Spaces", className="curve-section-title"),
                    dcc.Loading(
                        id="st-insights-loading",
                        type="default",
                        className="loading-parent insights-loading",
                        children=html.Div(
                            className="insights-loading-inner",
                            children=[
                                html.Div(
                                    className="curve-toolbar insights-toolbar",
                                    children=[
                                        html.Div(
                                            className="curve-toolbar-field insights-toolbar-field",
                                            children=[
                                                html.Label("Space", className="curve-toolbar-label"),
                                                dcc.Dropdown(
                                                    id="st-insights-space",
                                                    options=[],
                                                    value=None,
                                                    placeholder="Load spaces…",
                                                    clearable=False,
                                                    className="insights-space-select toolbar-select",
                                                    optionHeight=48,
                                                ),
                                            ],
                                        ),
                                        html.Button(
                                            "Refresh",
                                            id="st-insights-refresh",
                                            type="button",
                                            className="curve-refresh-btn",
                                        ),
                                    ],
                                ),
                                html.Div(id="st-insights-list-status", className="insights-list-status"),
                                html.Div(id="st-insights-space-detail"),
                            ],
                        ),
                    ),
                ],
            ),
        ],
    )


def layout() -> html.Div:
    return html.Div(
        className="page-curve page-insights",
        children=[
            _page_header(),
            ucp.presenter_modal(
                _PRESENTER_SECTIONS,
                modal_id="st-insights-presenter-modal",
                close_id="st-insights-presenter-close",
                backdrop_id="st-insights-presenter-backdrop",
                title_id="st-insights-presenter-modal-title",
                lead=_PRESENTER_LEAD,
            ),
            _insights_body(),
        ],
    )


@callback(
    Output("st-insights-presenter-modal", "className"),
    Input("st-insights-presenter-tip-btn", "n_clicks"),
    Input("st-insights-presenter-close", "n_clicks"),
    Input("st-insights-presenter-backdrop", "n_clicks"),
    State("st-insights-presenter-modal", "className"),
    prevent_initial_call=True,
)
def _toggle_presenter_modal(
    _open: int | None,
    _close: int | None,
    _backdrop: int | None,
    current_class: str | None,
) -> str:
    base = "curve-presenter-modal"
    open_cls = f"{base} curve-presenter-modal-open"
    if current_class and "curve-presenter-modal-open" in current_class:
        return base
    return open_cls


@callback(
    Output("st-insights-space", "options"),
    Output("st-insights-space", "value"),
    Output("st-insights-list-status", "children"),
    Input("st-insights-refresh", "n_clicks"),
    State("st-insights-space", "value"),
    prevent_initial_call=False,
)
def _load_genie_space_options(
    _n: int | None,
    current: str | None,
) -> tuple[list[dict[str, str]], str | None, html.Div]:
    spaces, err = gs.list_short_term_genie_spaces()
    if err:
        return [], None, _alert(
            f"Could not list Genie spaces: {err}. Run `databricks auth login` for the workspace profile used by this app.",
            kind="error",
        )
    if not spaces:
        return [], None, _alert(
            f"No Genie spaces found with title starting with “{gs.GENIE_TITLE_PREFIX_SHORT_TERM}”. "
            "Run notebook 04 (st04_trader_insights), then refresh.",
            kind="warn",
        )
    options = gs.options_for_dropdown(spaces)
    ids = [o["value"] for o in options]
    value = ucp.resolve_dropdown_value(current, ids)
    status = html.P(
        f"{len(spaces)} space(s) matching “{gs.GENIE_TITLE_PREFIX_SHORT_TERM}”.",
        className="curve-section-lead insights-list-status-text",
    )
    return options, value, status


@callback(
    Output("st-insights-space-detail", "children"),
    Input("st-insights-space", "value"),
    prevent_initial_call=False,
)
def _render_selected_space(space_id: str | None) -> html.Div:
    return _render_space_detail(space_id)
