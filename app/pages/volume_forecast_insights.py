"""
Renewables insights (Genie) — volume-forecasting natural-language analytics launcher.
Genie scope: modules/volume-forecasting/notebooks/genie_space_config.py (notebook 09).
"""

from __future__ import annotations

import dash
from dash import Input, Output, State, callback, dcc, html

import genie_spaces as gs
import uc_pages as ucp
import ui_icons as uicons

_PATH = "/volume-forecasting/insights"

dash.register_page(
    __name__,
    path=_PATH,
    name="Renewables insights (Genie)",
    title="Renewables insights (Genie) — Volume forecasting",
)

_PAGE_TITLE = "Renewables insights (Genie)"
_PAGE_SUMMARY = (
    "Ask plain-English questions over the same governed wind, solar, published net-volume, and "
    "accuracy tables the volume-forecasting desk already uses — without writing SQL. Choose a "
    "Genie Space below to read its description and sample prompts, then open it in the workspace "
    "with Agent mode enabled."
)

_GENIE_CALLOUT_TITLE = "Plain-English answers on the renewables volume desk"
_GENIE_CALLOUT_BODY = (
    "Before publish or a shift handover, the desk needs fleet P50, ensemble spread, curtailment and "
    "negative-price risk, and the euro cost of forecast error — without waiting on a quant. Genie "
    "lets you ask in everyday language: how wind and solar performed on the latest delivery date, "
    "what supply legs sit in the published net volume, or whether the WIND or SOLAR leg is drifting. "
    "Answers pull from the same volume_forecast_* gold tables as the Dash capability pages, so "
    "forecasting, risk, and short-term squaring share one story."
)

# App page only — Genie Space still has the full set from notebook 09.
_APP_DISPLAY_QUESTIONS: tuple[str, ...] = (
    "Show me renewables book performance — wind and solar P50, peaks, and risk flags on the latest delivery date.",
    "Which zones have HIGH wind curtailment risk on the latest delivery date?",
    "What is solar negative-price risk and midday peak by zone on the latest day?",
    "How much wind and solar supply is in the published net volume today?",
    "What is MAE and cash-out cost for the WIND and SOLAR legs at day-ahead lead time?",
)

_PRESENTER_LEAD = (
    f"{ucp.PRESENTER_LEAD_GENIE} Walk wind → solar → publication → accuracy first, then open Genie here."
)

_PRESENTER_SECTIONS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "1 — Pain point for traders",
        (
            "The question \"how is the renewables book performing today?\" spans wind fleet P50, solar midday risk, "
            "the published supply cut, and yesterday's cash-out — yet forecasters and traders still chase four tabs "
            "minutes before a publish gate.",
            "Publish handover needs one official number plus its risk flags. Asking in plain English feels dangerous if "
            "the answer might come from a different dataset than the dashboards everyone already trusted.",
            "Management asks for euros and MAE; operators ask for curtailment; the curve desk asks for net volume — the "
            "room wants one conversation, not a routing matrix to four subject-matter experts.",
        ),
    ),
    (
        "2 — Business problem this solves",
        (
            "Genie queries the same renewables volume-forecasting tables that power the structured dashboards — fleet "
            "performance, curtailment risk, published wind and solar supply, accuracy and cash-out by leg.",
            "Strong demo move: read a wind KPI aloud on the wind page, then open this page, restate the question in "
            "one sentence, and click the matching sample tile. Desks respect the demo when Genie returns the same number.",
            "Recommended walk order: wind, solar, publication, accuracy, then this page. Cross-cutting questions — "
            "\"published wind megawatts plus drift status\" — work here when siloed dashboards cannot answer in one breath. "
            "Open answers in the workspace to prove SQL lineage when challenged; state upfront these are illustrative "
            "demo figures, not live TSO or vendor feeds.",
        ),
    ),
    (
        "3 — This page and each widget",
        (
            "Page title and summary: Renewables Insights — conversational access to the volume-forecasting Genie space. "
            "You are closing the renewables arc, not opening it cold.",
            "Page callout: Read the accent callout if the audience skipped wind, solar, publication, or accuracy. It "
            "frames wind, solar, official net volume, and priced accuracy as one desk story.",
            "Genie space dropdown: Select the renewables volume-forecasting space and confirm the status line shows "
            "available before you promise a live answer. Refresh once if the list is empty.",
            "Space description panel: Read what question types the space supports. Open in workspace when you want to "
            "show the forecaster-style chat experience during a busy publish window.",
            "Sample question tiles: Curtailment by zone, solar negative-price risk, published wind and solar supply, "
            "MAE and cash-out by leg — pick the tile that continues the narrative from the page you just showed.",
            "Running Genie: Restate the question in desk language before clicking. Enable conversational agent mode if "
            "available. Keep delivery date consistent with the dashboards when you say \"today\" or \"latest day.\"",
            "Close with conviction: \"Four governed views give structure and auditability — Genie gives the cross-leg "
            "answer you need before you sign the publish cut.\"",
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
                            html.Span("Volume forecasting", className="curve-page-eyebrow"),
                            html.Span("Genie", className="curve-page-badge curve-page-badge-ml"),
                            html.Span("Natural language", className="curve-page-badge"),
                        ],
                    ),
                    ucp.presenter_tip_button("vf-insights-presenter-tip-btn"),
                ],
            ),
            uicons.hero_title(_PAGE_TITLE, uicons.VOLUME_FORECAST_NAV_ICONS[_PATH]),
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
        "Starter questions for the demo (wind, solar, publication, accuracy). In Genie, turn on Agent mode and pick a tile—or ask your own."
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
                        id="vf-insights-loading",
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
                                                    id="vf-insights-space",
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
                                            id="vf-insights-refresh",
                                            type="button",
                                            className="curve-refresh-btn",
                                        ),
                                    ],
                                ),
                                html.Div(id="vf-insights-list-status", className="insights-list-status"),
                                html.Div(id="vf-insights-space-detail"),
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
                modal_id="vf-insights-presenter-modal",
                close_id="vf-insights-presenter-close",
                backdrop_id="vf-insights-presenter-backdrop",
                title_id="vf-insights-presenter-modal-title",
                lead=_PRESENTER_LEAD,
            ),
            _insights_body(),
        ],
    )


@callback(
    Output("vf-insights-presenter-modal", "className"),
    Input("vf-insights-presenter-tip-btn", "n_clicks"),
    Input("vf-insights-presenter-close", "n_clicks"),
    Input("vf-insights-presenter-backdrop", "n_clicks"),
    State("vf-insights-presenter-modal", "className"),
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
    Output("vf-insights-space", "options"),
    Output("vf-insights-space", "value"),
    Output("vf-insights-list-status", "children"),
    Input("vf-insights-refresh", "n_clicks"),
    State("vf-insights-space", "value"),
    prevent_initial_call=False,
)
def _load_genie_space_options(
    _n: int | None,
    current: str | None,
) -> tuple[list[dict[str, str]], str | None, html.Div]:
    spaces, err = gs.list_renewables_genie_spaces()
    if err:
        return [], None, _alert(
            f"Could not list Genie spaces: {err}. Run `databricks auth login` for the workspace profile used by this app.",
            kind="error",
        )
    if not spaces:
        return [], None, _alert(
            f"No Genie spaces found with title starting with “{gs.GENIE_TITLE_PREFIX_RENEWABLES}”. "
            "Run notebook 09 (vf09_renewables_insights_genie), then refresh.",
            kind="warn",
        )
    options = gs.options_for_dropdown(spaces)
    ids = [o["value"] for o in options]
    value = ucp.resolve_dropdown_value(current, ids)
    status = html.P(
        f"{len(spaces)} space(s) matching “{gs.GENIE_TITLE_PREFIX_RENEWABLES}”.",
        className="curve-section-lead insights-list-status-text",
    )
    return options, value, status


@callback(
    Output("vf-insights-space-detail", "children"),
    Input("vf-insights-space", "value"),
    prevent_initial_call=False,
)
def _render_selected_space(space_id: str | None) -> html.Div:
    return _render_space_detail(space_id)
