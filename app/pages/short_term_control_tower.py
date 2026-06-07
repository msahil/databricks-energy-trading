"""
24/7 Operations & Live Dispatch — control tower dashboard.
Spec: modules/short-term/specifications/02-operations-live-dispatch.md
"""

from __future__ import annotations

from typing import Any

import dash
from dash import Input, Output, State, callback, dcc, html
import plotly.graph_objects as go

import uc_pages as ucp
import ui_icons as uicons

dash.register_page(
    __name__,
    path="/short-term/control-tower",
    name="Control Tower",
    title="24/7 Operations & Live Dispatch — Short-term trading",
)

_PAGE_TITLE = "24/7 Operations & Live Dispatch"
_PAGE_SUMMARY = (
    "The operations control tower for the 1,000 MW physical book. Balance squaring and DSR dispatch "
    "in one ribbon, see per-asset Mosaic AI recommendations, grid frequency and market gates, streamed "
    "REMIT events, and an agentic copilot that drafts the play with rationale. Operator keeps the "
    "decision — the platform removes analytical lag."
)

_KPI_LEAD = (
    "Shift-level headline: book balance state, P&L since handover, open alerts, and critical events — "
    "the first screen the operations trader checks when taking or handing over the desk."
)
_WIDGET_BALANCE = (
    "Combines near-delivery squaring delta with verified DSR dispatch into one net position ribbon. "
    "Shows whether the physical book is balanced, exposed, or relying on flex through the trading day."
)
_WIDGET_ASSETS = (
    "Live output, state of charge, and Mosaic AI recommended action for each owned asset at your interval cursor. "
    "Helps operators decide what to curtail, dispatch, or hold before the next gate closes."
)
_WIDGET_GRID = (
    "TSO frequency and aFRR/mFRR signals by zone. Tells you whether the grid is tight and calling flex up or down — "
    "context for intraday price spikes and DSR dispatch triggers."
)
_WIDGET_GATES = (
    "Minutes to cross-border gate close, order-book depth, and gate status per market. "
    "Traders use this to time XBID squaring orders before intervals lock."
)
_WIDGET_REMIT = (
    "Structural outages and REMIT events that can move intraday prices. "
    "Gives operators and traders shared situational awareness without switching consoles."
)
_WIDGET_COPILOT = (
    "Agentic recommendation with rationale and expected P&L impact — decision support only. "
    "Surfaces the next best action when balance, grid, and event feeds align."
)
_WIDGET_HANDOVER = (
    "Structured notes from the previous shift so the incoming trader knows open risks, pending actions, "
    "and what still needs a human sign-off."
)

_PRESENTER_SECTIONS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "1 — Pain point for traders",
        (
            "Operations traders run a 24/7 book, but dispatch screens, grid-frequency feeds, gate clocks, outage portals, "
            "and squaring tools usually live in different systems. Precious minutes pass while the book moves against them — "
            "and the incoming shift inherits confusion instead of a clear picture.",
            "This portfolio is not only owned generation and batteries. Thousands of megawatts of aggregated demand-side flex "
            "also move the net balance, yet most platforms never show squaring delta and verified VPP dispatch in the same "
            "ribbon. The operator cannot answer the question traders care about: \"Are we actually balanced into the next "
            "intervals, or are we relying on hope?\"",
            "When a French nuclear trip or an evening scarcity event hits, the room does not want five tabs and a phone "
            "tree. They want one shift headline, one interval cursor, and a recommendation they can accept or reject — "
            "with rationale a skeptical trader can challenge.",
        ),
    ),
    (
        "2 — Business problem this solves",
        (
            "This page is the operations control tower: shift-level headline, interval cursor across the trading day, a "
            "balance ribbon that combines near-delivery squaring with verified flex dispatch, per-asset Mosaic "
            "recommendations, grid and gate context, a ranked REMIT feed, and an agentic copilot that drafts the next "
            "play with expected P&L — always with a human in the loop.",
            "The numbers should tell one story with the squaring desk and the VPP desk. Squaring exposure from "
            "near-delivery rolls into the balance ribbon; verified flex from DSR appears beside owned-asset dispatch on "
            "the same trade date. That is how modern desks survive volatile quarter-hours.",
            "Decision support with an audit trail — handover notes, rationale, confidence — cuts analytical lag without "
            "auto-trading. Operators stay in control; management sees 24/7 discipline. A strong demo arc: show a severe "
            "forecast deviation on near-delivery, then open this page, read EXPOSED on the banner, walk the copilot "
            "recommendation, and close on handover notes for the next shift.",
        ),
    ),
    (
        "3 — This page and each widget",
        (
            "Page title and summary: Frame this as 24/7 Operations and Live Dispatch — not a second squaring screen, but "
            "where the physical book is run around the clock. Mention the 1,000 MW owned book plus aggregated flex in one "
            "sentence so traders know the scope.",
            "Toolbar: Keep trade date aligned with near-delivery and DSR so you are telling one operating day. The "
            "interval cursor is powerful — explain it as moving \"now\" across quarter-hours; asset dispatch and grid "
            "panels update with the cursor, which mirrors how operators think. Use zone when you want Germany-specific "
            "grid or gate detail. Refresh when the room asks for the latest snapshot.",
            "Status banner: Lead with balance state — BALANCED versus EXPOSED. Exposed should sound like a call to "
            "action, not a colour label. Read the headline as the shift story (evening scarcity, outage-driven short, "
            "and so on). Point at P&L since handover, open alerts, and critical events — say \"this is what you would "
            "scan in the first thirty seconds before trusting anything below.\"",
            "Desk headline (text under the banner): This one-line framing asks \"Are we balanced into the next "
            "intervals?\" Pause here; novice presenters rush past it, but traders appreciate a breath before detail.",
            "Balance ribbon chart: Introduce net position through the day, split into squaring delta and flex "
            "contribution where visible. Ask aloud: \"Do owned assets plus aggregated flex cover what we nominated each "
            "quarter-hour?\" When the banner said EXPOSED, tie it explicitly to the worst intervals on the ribbon. If "
            "flex contribution is flat, say the VPP was not dispatched in this scenario — do not gloss over it.",
            "Asset dispatch cards: At the selected interval, each card shows live output, state of charge, recommended "
            "action, and expected margin. For the battery, talk charge, hold, or discharge in terms traders know — "
            "cycle headroom and intraday spread. For gas, mention ramp state and clean spark spread. Constraint flags "
            "prove the recommendation respects real limits.",
            "Grid and frequency panel: Set context — \"Is the grid tight and calling flex up or down?\" Walk one row: "
            "frequency, balancing activation, signal state. You do not need engineering depth; connect grid stress to "
            "why dispatch and intraday price moved. Move the interval cursor once so the room sees signals evolve.",
            "Market gates table: Traders know gate clocks intimately. Say minutes to close out loud; link shallow "
            "order-book depth to slippage risk. Pair verbally with near-delivery: gates here, recommended buys and "
            "sells there — same deadline. CLOSED means continuous intraday is over.",
            "REMIT and event feed: Present this as ranked situational awareness when something breaks. For one critical "
            "row, read capacity and price impact and say what that might do to merit order and spreads. The classic "
            "anchor — French nuclear trip rippling into German intraday — works if a matching row is on screen.",
            "Trading copilot: Read the top recommendation and rationale like a colleague, not a vendor. Expected P&L "
            "and confidence are what traders challenge first. Stress that nothing executes automatically. If Genie comes "
            "up later, contrast gently: copilot is curated for this moment on this book; Genie answers follow-up questions.",
            "Shift handover: Read notes aloud even if short — shift start time is the audit anchor. This signals "
            "operations is a process, not only a dashboard.",
            "Close with conviction: \"Squaring, flex, grid, outages, and the next play — one interval cursor, one "
            "governed lakehouse cut the whole desk can argue from.\"",
        ),
    ),
)


def _alert(message: str, *, kind: str = "warn") -> html.Div:
    return html.Div(message, className=f"curve-alert curve-alert-{kind}")


def _outcome_card(title: str, value: str, *, sub: str | None = None, variant: str = "") -> html.Div:
    return html.Div(
        className=f"curve-outcome-card {variant}".strip(),
        children=[
            html.Div(title, className="curve-outcome-label"),
            html.Div(value, className="curve-outcome-value"),
            html.Div(sub, className="curve-outcome-sub") if sub else None,
        ],
    )


def _table(headers: list[str], rows: list[list[Any]]) -> html.Table:
    return html.Table(
        className="curve-data-table",
        children=[
            html.Thead(html.Tr([html.Th(h) for h in headers])),
            html.Tbody([html.Tr([html.Td(str(c)) for c in row]) for row in rows]),
        ],
    )


def _balance_chart(rows: list[list[Any]]) -> go.Figure:
    fig = go.Figure()
    if not rows:
        fig.update_layout(title="Portfolio balance ribbon", template="plotly_white", height=280)
        return fig
    xs = [str(r[0]) for r in rows]
    net = [float(r[1] or 0) for r in rows]
    sq = [float(r[2] or 0) for r in rows]
    dsr = [float(r[3] or 0) for r in rows]
    fig.add_trace(go.Scatter(x=xs, y=net, mode="lines", name="Net position", line=dict(width=3)))
    fig.add_trace(go.Scatter(x=xs, y=sq, mode="lines", name="Squaring", line=dict(dash="dot")))
    fig.add_trace(go.Scatter(x=xs, y=dsr, mode="lines", name="DSR", line=dict(dash="dot")))
    fig.update_layout(
        title="Net position by interval (squaring + DSR)",
        yaxis_title="MW",
        template="plotly_white",
        height=280,
        margin=dict(l=48, r=16, t=48, b=80),
        xaxis_tickangle=-45,
        legend=dict(orientation="h"),
    )
    return fig


def _asset_card(row: list[Any]) -> html.Div:
    asset_id, atype, out, soc, action, margin, flag = row[:7]
    return html.Div(
        className="curve-outcome-card",
        children=[
            html.Div(str(asset_id), className="curve-outcome-label"),
            html.Div(str(action), className="curve-outcome-value"),
            html.Div(
                f"{float(out or 0):.1f} MW"
                + (f" · SoC {float(soc):.0f}%" if soc not in (None, "") else "")
                + (f" · €{float(margin):,.0f}" if margin not in (None, "") else ""),
                className="curve-outcome-sub",
            ),
            html.Div(str(flag or "OK"), className="curve-kpi-sub") if flag and flag != "OK" else None,
        ],
    )


def layout() -> html.Div:
    return html.Div(
        className="page-curve",
        children=[
            html.Header(
                className="curve-page-hero",
                children=[
                    html.Div(
                        className="curve-page-hero-head",
                        children=[
                            html.Div(
                                className="curve-page-hero-top",
                                children=[
                                    html.Span("Short-term trading", className="curve-page-eyebrow"),
                                    html.Span("Operations", className="curve-page-badge"),
                                    html.Span("Mosaic AI", className="curve-page-badge"),
                                ],
                            ),
                            ucp.presenter_tip_button("st-tower-presenter-tip-btn"),
                        ],
                    ),
                    uicons.hero_title(_PAGE_TITLE, uicons.SHORT_TERM_NAV_ICONS["/short-term/control-tower"]),
                    html.P(_PAGE_SUMMARY, className="curve-page-summary"),
                ],
            ),
            ucp.presenter_modal(
                _PRESENTER_SECTIONS,
                modal_id="st-tower-presenter-modal",
                close_id="st-tower-presenter-close",
                backdrop_id="st-tower-presenter-backdrop",
                title_id="st-tower-presenter-modal-title",
            ),
            html.Div(
                className="curve-callout curve-callout-accent",
                children=html.P(
                    "One operations view across squaring, flex dispatch, grid signals, and market gates — "
                    "so the trader acts on a single source of truth instead of five separate tools.",
                    className="curve-callout-body",
                ),
            ),
            html.Div(
                className="curve-toolbar st-toolbar",
                children=[
                    html.Div(
                        className="curve-toolbar-field st-toolbar-field-date",
                        children=[
                            html.Label("Trade date", className="curve-toolbar-label"),
                            dcc.Dropdown(
                                id="st-tower-date",
                                options=[],
                                value=None,
                                clearable=False,
                                className="toolbar-select st-toolbar-date",
                                optionHeight=44,
                            ),
                        ],
                    ),
                    html.Div(
                        className="curve-toolbar-field st-toolbar-field-interval",
                        children=[
                            html.Label("Interval cursor", className="curve-toolbar-label"),
                            dcc.Dropdown(
                                id="st-tower-interval",
                                options=[],
                                value=None,
                                clearable=False,
                                className="toolbar-select st-toolbar-interval",
                                optionHeight=44,
                            ),
                        ],
                    ),
                    html.Div(
                        className="curve-toolbar-field st-toolbar-field-zone",
                        children=[
                            html.Label("Zone", className="curve-toolbar-label"),
                            dcc.Dropdown(
                                id="st-tower-zone",
                                options=[{"label": "All zones", "value": "ALL"}],
                                value="ALL",
                                clearable=False,
                                className="toolbar-select st-toolbar-zone",
                                optionHeight=44,
                            ),
                        ],
                    ),
                    html.Button("Refresh", id="st-tower-refresh", type="button", className="curve-refresh-btn"),
                ],
            ),
            dcc.Loading(id="st-tower-loading", type="default", children=html.Div(id="st-tower-body")),
        ],
    )


def _body(
    warehouse_id: str,
    delivery_date: str,
    interval_index: int,
    zone: str,
) -> html.Div:
    dp = ucp.sql_delivery_date_predicate("delivery_date", delivery_date)
    dp_d = ucp.sql_delivery_date_predicate("d.delivery_date", delivery_date)
    dp_f = ucp.sql_delivery_date_predicate("f.delivery_date", delivery_date)
    idx = int(interval_index)
    z_pred = "" if zone == "ALL" else f" AND zone_code = '{ucp.sql_escape(zone)}'"
    z_freq = "" if zone == "ALL" else f" AND f.zone_code = '{ucp.sql_escape(zone)}'"

    sum_sql = f"""
    SELECT headline, balance_state, pnl_since_shift_eur, n_open_alerts, n_critical_events,
           handover_notes, shift_start_ts, top_copilot_recommendation_id
    FROM {ucp.fq("short_term_gold_control_tower_summary")}
    WHERE {dp}
    LIMIT 1
    """
    sum_res = ucp.run_uc_sql(warehouse_id, sum_sql)
    if not sum_res.ok:
        return _alert(sum_res.error or "Summary failed", kind="error")

    parts: list[Any] = []
    if sum_res.rows:
        s = dict(zip(sum_res.columns, sum_res.rows[0]))
        state = str(s.get("balance_state") or "")
        cls = "curve-pub-draft" if state == "EXPOSED" else "curve-pub-official"
        parts.append(
            html.Div(
                className=f"curve-publication-banner {cls}",
                children=[
                    html.Span(state, className="curve-pub-badge"),
                    html.Span(str(s.get("headline") or ""), className="curve-pub-headline"),
                    html.Span(
                        f"P&L since shift €{float(s.get('pnl_since_shift_eur') or 0):,.0f} · "
                        f"{int(float(s.get('n_open_alerts') or 0))} alerts · "
                        f"{int(float(s.get('n_critical_events') or 0))} critical events",
                        className="curve-pub-meta",
                    ),
                ],
            )
        )
        parts.append(html.P(_KPI_LEAD, className="curve-section-lead"))

    bal_sql = f"""
    SELECT interval_start, net_position_mw, squaring_delta_mw, dsr_contribution_mw, balance_state
    FROM {ucp.fq("short_term_gold_portfolio_balance")}
    WHERE {dp}
    ORDER BY interval_start
    """
    disp_sql = f"""
    SELECT d.asset_id, d.asset_type, d.current_output_mw, d.soc_pct, d.recommended_action,
           d.expected_margin_eur, d.constraint_flag
    FROM {ucp.fq("short_term_gold_asset_dispatch")} d
    INNER JOIN {ucp.fq("short_term_dim_intervals")} i
      ON d.delivery_date = i.delivery_date AND d.interval_start = i.interval_start
    WHERE {dp_d} AND i.interval_index = {idx}
    ORDER BY d.asset_id
    """
    freq_sql = f"""
    SELECT f.zone_code, f.frequency_hz, f.frequency_deviation_mhz, f.afrr_signal_mw, f.mfrr_signal_mw, f.signal_state
    FROM {ucp.fq("short_term_silver_grid_frequency")} f
    INNER JOIN {ucp.fq("short_term_dim_intervals")} i
      ON f.delivery_date = i.delivery_date AND f.interval_start = i.interval_start
    WHERE {dp_f} AND i.interval_index = {idx}{z_freq}
    ORDER BY f.zone_code
    """
    gate_sql = f"""
    SELECT market, zone_code, minutes_to_gate, order_book_depth_mw, gate_status, best_bid_eur_mwh
    FROM {ucp.fq("short_term_silver_market_gates")}
    WHERE {dp}{z_pred}
    ORDER BY minutes_to_gate
    """
    remit_sql = f"""
    SELECT event_ts, event_type, affected_zone, capacity_mw, impact_eur_mwh, severity, asset_or_unit
    FROM {ucp.fq("short_term_gold_remit_events")}
    WHERE {dp}
    ORDER BY CASE severity WHEN 'CRITICAL' THEN 1 WHEN 'WATCH' THEN 2 ELSE 3 END, event_ts DESC
    LIMIT 15
    """
    cop_sql = f"""
    SELECT recommendation_id, recommendation, rationale, expected_pnl_impact_eur, confidence, agent_trace, status
    FROM {ucp.fq("short_term_gold_copilot_recommendations")}
    WHERE {dp}
    ORDER BY confidence DESC
    LIMIT 3
    """

    bal_res = ucp.run_uc_sql(warehouse_id, bal_sql)
    disp_res = ucp.run_uc_sql(warehouse_id, disp_sql)
    freq_res = ucp.run_uc_sql(warehouse_id, freq_sql)
    gate_res = ucp.run_uc_sql(warehouse_id, gate_sql)
    remit_res = ucp.run_uc_sql(warehouse_id, remit_sql)
    cop_res = ucp.run_uc_sql(warehouse_id, cop_sql)

    dsr_note = None
    if bal_res.ok and bal_res.rows:
        has_dsr = any(abs(float(r[3] or 0)) > 0.01 for r in bal_res.rows)
        if not has_dsr:
            dsr_note = _alert("DSR contribution is zero — notebook 03 may not have run.", kind="warn")

    parts.append(
        ucp.capability_section(
            "Balance ribbon",
            _WIDGET_BALANCE,
            dsr_note,
            dcc.Graph(figure=_balance_chart(bal_res.rows if bal_res.ok else []), config={"displayModeBar": False}),
        )
    )

    asset_cards = (
        html.Div(className="curve-outcome-row", children=[_asset_card(r) for r in disp_res.rows])
        if disp_res.ok and disp_res.rows
        else html.P("No asset dispatch rows for this interval.", className="curve-muted")
    )
    parts.append(ucp.capability_section("Asset dispatch", _WIDGET_ASSETS, asset_cards))

    parts.append(
        ucp.capability_section(
            "Grid & frequency",
            _WIDGET_GRID,
            _table(
                ["Zone", "Hz", "Δ mHz", "aFRR MW", "mFRR MW", "State"],
                [
                    [r[0], f"{float(r[1]):.4f}", f"{float(r[2]):.1f}", f"{float(r[3]):.1f}", f"{float(r[4]):.1f}", r[5]]
                    for r in (freq_res.rows if freq_res.ok else [])
                ],
            )
            if freq_res.ok and freq_res.rows
            else html.P("No frequency data.", className="curve-muted"),
        )
    )

    parts.append(
        ucp.capability_section(
            "Market gates",
            _WIDGET_GATES,
            _table(
                ["Market", "Zone", "Mins to gate", "Depth MW", "Status", "Best bid"],
                gate_res.rows if gate_res.ok and gate_res.rows else [],
            )
            if gate_res.ok and gate_res.rows
            else html.P("No gate data.", className="curve-muted"),
        )
    )

    parts.append(
        ucp.capability_section(
            "REMIT & event feed",
            _WIDGET_REMIT,
            _table(
                ["Time", "Type", "Zone", "MW", "Impact €/MWh", "Severity", "Unit"],
                remit_res.rows if remit_res.ok and remit_res.rows else [],
            )
            if remit_res.ok and remit_res.rows
            else html.P("No events.", className="curve-muted"),
        )
    )

    if cop_res.ok and cop_res.rows:
        top = cop_res.rows[0]
        parts.append(
            ucp.capability_section(
                "Trading copilot",
                _WIDGET_COPILOT,
                html.Div(
                    className="curve-callout curve-callout-accent",
                    children=[
                        html.P(str(top[1]), className="curve-callout-title"),
                        html.P(str(top[2]), className="curve-callout-body"),
                        html.P(
                            f"Expected impact €{float(top[3]):,.0f} · confidence {float(top[4]):.0%} · {top[5]}",
                            className="curve-kpi-sub",
                        ),
                    ],
                ),
            )
        )

    if sum_res.rows:
        s = dict(zip(sum_res.columns, sum_res.rows[0]))
        parts.append(
            ucp.capability_section(
                "Shift handover",
                _WIDGET_HANDOVER,
                html.P(str(s.get("handover_notes") or ""), className="curve-muted"),
                html.P(f"Shift started {s.get('shift_start_ts') or '—'}", className="curve-muted"),
            )
        )

    parts.append(
        html.P(
            f"Cursor: {delivery_date} · interval {interval_index}. Recommendations are decision support only.",
            className="curve-footnote",
        )
    )
    return html.Div(className="curve-page-body", children=parts)


@callback(
    Output("st-tower-date", "options"),
    Output("st-tower-date", "value"),
    Output("st-tower-zone", "options"),
    Output("st-tower-zone", "value"),
    Input("sql-warehouse-dropdown", "value"),
    Input("st-tower-refresh", "n_clicks"),
    State("st-tower-date", "value"),
    State("st-tower-zone", "value"),
    prevent_initial_call=False,
)
def _load_date_zone(
    warehouse_id: str | None,
    _n: int | None,
    current_date: str | None,
    current_zone: str | None,
):
    z_opts = [{"label": "All zones", "value": "ALL"}]
    if not warehouse_id:
        return [], None, z_opts, ucp.resolve_dropdown_value(current_zone, ["ALL"])
    d_sql = f"SELECT DISTINCT delivery_date FROM {ucp.fq('short_term_dim_intervals')} ORDER BY delivery_date DESC"
    z_sql = f"SELECT zone_code FROM {ucp.fq('short_term_dim_zones')} ORDER BY zone_code"
    d_res = ucp.run_uc_sql(warehouse_id, d_sql)
    z_res = ucp.run_uc_sql(warehouse_id, z_sql)
    dates = [ucp.normalize_as_of(r[0]) for r in (d_res.rows if d_res.ok else []) if ucp.normalize_as_of(r[0])]
    z_opts += [{"label": str(r[0]), "value": str(r[0])} for r in (z_res.rows if z_res.ok else [])]
    z_values = [str(o["value"]) for o in z_opts]
    return (
        [{"label": d, "value": d} for d in dates],
        ucp.resolve_dropdown_value(current_date, dates),
        z_opts,
        ucp.resolve_dropdown_value(current_zone, z_values),
    )


@callback(
    Output("st-tower-interval", "options"),
    Output("st-tower-interval", "value"),
    Input("sql-warehouse-dropdown", "value"),
    Input("st-tower-date", "value"),
    Input("st-tower-refresh", "n_clicks"),
    State("st-tower-interval", "value"),
    prevent_initial_call=False,
)
def _load_intervals(warehouse_id: str | None, delivery_date: str | None, _n: int | None, current: str | None):
    if not warehouse_id or not delivery_date:
        return [], None
    dp = ucp.sql_delivery_date_predicate("delivery_date", delivery_date)
    sql = f"""
    SELECT interval_start, interval_index
    FROM {ucp.fq("short_term_dim_intervals")}
    WHERE {dp}
    ORDER BY interval_start
    """
    res = ucp.run_uc_sql(warehouse_id, sql)
    if not res.ok or not res.rows:
        return [], None
    opts = [{"label": f"#{r[1]} — {r[0]}", "value": str(int(r[1]))} for r in res.rows]
    values = [str(int(r[1])) for r in res.rows]
    return opts, ucp.resolve_dropdown_value(current, values)


@callback(
    Output("st-tower-body", "children"),
    Input("sql-warehouse-dropdown", "value"),
    Input("st-tower-date", "value"),
    Input("st-tower-interval", "value"),
    Input("st-tower-zone", "value"),
    Input("st-tower-refresh", "n_clicks"),
)
def _render(
    warehouse_id: str | None,
    delivery_date: str | None,
    interval_index: str | None,
    zone: str | None,
    _n: int | None,
):
    if not warehouse_id:
        return ucp.warehouse_prompt()
    if not delivery_date or not interval_index:
        return _alert(
            "No control-tower data. Run `energy_trading_demo_data` (01 → 03 → 02), then refresh.",
            kind="warn",
        )
    try:
        idx = int(interval_index)
    except (TypeError, ValueError):
        return _alert("Invalid interval cursor.", kind="error")
    return _body(
        warehouse_id,
        ucp.normalize_as_of(delivery_date) or delivery_date,
        idx,
        zone or "ALL",
    )


@callback(
    Output("st-tower-presenter-modal", "className"),
    Input("st-tower-presenter-tip-btn", "n_clicks"),
    Input("st-tower-presenter-close", "n_clicks"),
    Input("st-tower-presenter-backdrop", "n_clicks"),
    State("st-tower-presenter-modal", "className"),
    prevent_initial_call=True,
)
def _toggle_presenter(_o, _c, _b, current: str | None):
    base = "curve-presenter-modal"
    return base if current and "curve-presenter-modal-open" in current else f"{base} curve-presenter-modal-open"
