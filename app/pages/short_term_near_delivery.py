"""
Trading near delivery — short-term squaring desk.
Spec: modules/short-term/specifications/01-trading-near-delivery.md
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
    path="/short-term/near-delivery",
    name="Trading near delivery",
    title="Trading near delivery — Short-term trading",
)

_PAGE_TITLE = "Trading near delivery"
_PAGE_SUMMARY = (
    "The intraday squaring desk in one place. See where the book is long or short before each "
    "15-minute gate closes, which assets are deviating from the last re-forecast, and what cash-out "
    "exposure looks like if you stay unbalanced into delivery. Replay backtested squaring rules to "
    "prove a strategy before arming it live — same gold tables the control tower reads for the "
    "balance ribbon."
)

_KPI_LEAD = (
    "Your at-a-glance desk position for the selected day: open volume still to square, gates closing soon, "
    "assets in severe deviation, and projected TSO cash-out if you enter delivery unbalanced."
)
_WIDGET_SQUARING = (
    "Shows the recommended buy or sell per 15-minute interval before XBID gates close. "
    "Use it to neutralise the physical delta against your long-term hedge instead of paying imbalance prices."
)
_WIDGET_DEVIATIONS = (
    "Flags assets where the latest weather-driven re-forecast moved materially. "
    "Prioritise these intervals first — they are where your position is most likely to drift before gate close."
)
_WIDGET_IMBALANCE = (
    "Projects cash-out if commercial nominations and live metering stay misaligned into delivery. "
    "Helps you decide whether to square now or accept the TSO imbalance charge."
)
_WIDGET_BACKTEST = (
    "Replays squaring rules on historical intervals before you arm them live. "
    "Compare realised P&L, hit rate, and cash-out avoided to pick a strategy with evidence."
)

_PRESENTER_SECTIONS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "1 — Pain point for traders",
        (
            "Every morning the curve desk hands the prompt desk a hedge — forwards, nominations, a plan for the day. "
            "By midday that plan is already wrong: wind ramps up or drops off, cloud cover eats solar, and the physical "
            "book drifts long or short while the trader still has open intervals to fix.",
            "Cross-border continuous markets (XBID) only stay open until a few minutes before each 15-minute delivery block. "
            "Miss that window and the transmission system operator steps in with balancing reserves — billing a steep "
            "imbalance price for every megawatt-hour they are still wrong-sided. Traders feel that clock in their bones.",
            "In live operations the answer to \"how exposed am I?\" is scattered across forecast portals, squaring tools, "
            "and spreadsheets. With gates closing, there is no time to reconcile five versions of the truth. The desk "
            "needs one screen that says: here is your residual position, here is what moved on the latest weather run, "
            "here is what to buy or sell, and here is what you pay if you wait.",
        ),
    ),
    (
        "2 — Business problem this solves",
        (
            "This page is the squaring desk control room on a single governed snapshot: net open position, forecast "
            "surprises ranked by severity, a recommended buy/sell programme aligned to open gates, projected imbalance "
            "cash-out in euros, and a backtest that proves the squaring rule before anyone arms it live.",
            "Near-delivery is the last mile of the trade. The hedge from the curve desk is the starting point — not the "
            "finish line. Prompt traders square what weather actually produced versus what was nominated; that is the "
            "commercial reality before electrons must be delivered.",
            "Squaring on the intraday market is almost always cheaper than entering delivery imbalanced and paying the "
            "TSO. Risk and finance care because projected cash-out on this page is the same curve they watch when "
            "intraday P&L starts swinging. Operations cares because severe deviations here are the same story they "
            "see on the control tower balance ribbon — same delivery day, same numbers.",
            "When you need a line that lands with an experienced room, say: \"The curve desk published the hedge this "
            "morning; this desk squares the residual before the gate shuts — on data everyone already trusts.\"",
        ),
    ),
    (
        "3 — This page and each widget",
        (
            "Page title and summary: Open on Trading near delivery. Read the subtitle if helpful — it frames the prompt "
            "desk squaring the physical book against the hedge before each gate closes. You are not showing a generic "
            "dashboard; you are showing where money is made or lost in the final hour before delivery.",
            "Toolbar (filters): Point at the trade date control first. Explain you can roll back to a prior delivery day "
            "to replay a decision or compare how the desk would have squared differently — useful when a trader asks "
            "\"what would we have done yesterday?\" The zone filter focuses on Germany, the Netherlands, France, or the "
            "whole portfolio; pick the market that matches the weather story you are telling. If the page looks empty, "
            "select a running SQL warehouse in the header and press Refresh — say out loud that traders expect a current "
            "snapshot, not yesterday's cache.",
            "Status banner: Start with system balance direction — SHORT or LONG. In plain terms: a SHORT system balance "
            "means the grid is structurally tight (buy bias); LONG means the system is long (sell bias). That context "
            "shapes how traders read the rest of the screen. Read the headline aloud; it should sound like a shift lead "
            "on a morning call (cloud hitting solar, gate pressure in Germany, and so on). Finish the banner with next "
            "gate close and net open megawatts — traders hear that as the clock and the open risk in one breath.",
            "Desk KPI cards — Net open position: \"This is what we still need to square against the hedge — our residual "
            "long or short in megawatts.\" Intervals open: \"These quarter-hours still accept continuous intraday orders.\" "
            "Intervals closing: if this number is above zero, pause and say \"We are running out of runway — gates are "
            "closing soon.\" Severe deviations: \"This many assets moved enough on the latest forecast that we should "
            "look at them first.\" Projected cash-out: \"If we enter delivery like this, this is the imbalance penalty "
            "we are staring at — the cost of doing nothing.\"",
            "Squaring actions chart: Introduce this as the desk's recommended buy/sell programme, interval by interval, "
            "while gates are still OPEN. When a gate shows CLOSED, explain honestly: continuous intraday is over; "
            "balancing products or accepting imbalance are the only options left. The takeaway you want traders to nod "
            "at: square here on the market instead of paying the TSO later. If someone asks about economics, use the "
            "expected price column to talk day-ahead versus intraday spread — familiar desk language.",
            "Forecast deviations table: Describe this as where the latest weather-driven forecast moved versus the "
            "previous run. Traders care because that is where their position will slip next — often before they feel "
            "it in P&L. Call out SEVERE rows before WATCH rows; say you would square those assets or intervals first. "
            "If the table is quiet on this date, switch trade date or zone rather than apologising — pick a day with a "
            "visible story.",
            "Imbalance and cash-out chart: Set it up as \"what we pay interval by interval if our commercial promises "
            "and actual output stay misaligned into delivery.\" When you see a spike, use it to justify urgency: "
            "\"That is why the desk is squaring now rather than hoping the forecast recovers.\" Mention that risk and "
            "finance teams watch this curve too — it is not only a trader screen.",
            "Backtest table: Frame this as evidence before going live — \"we replayed prior delivery days before "
            "trusting this rule.\" Walk one row slowly: realised P&L, cash-out avoided, hit rate. The row marked "
            "recommended is the rule the desk would arm. Land the governance point: the same lakehouse tables feed "
            "this live page and the backtest — traders and quants are not arguing from different spreadsheets.",
            "Close with conviction: \"Every quarter-hour on this screen is the same governed cut the operations control "
            "tower sees — one book, one deadline, one source of truth.\"",
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


def _squaring_chart(rows: list[list[Any]]) -> go.Figure:
    fig = go.Figure()
    if not rows:
        fig.update_layout(title="Net delta by interval", template="plotly_white", height=320)
        return fig
    xs, ys, colors, texts = [], [], [], []
    for row in rows:
        xs.append(str(row[0]))
        try:
            delta = float(row[1])
        except (TypeError, ValueError):
            continue
        ys.append(delta)
        side = str(row[2] or "FLAT")
        colors.append("#22c55e" if side == "BUY" else "#ef4444" if side == "SELL" else "#94a3b8")
        texts.append(f"{side} · gate {row[3]}")
    fig.add_trace(
        go.Bar(x=xs, y=ys, marker_color=colors, text=texts, hovertemplate="%{x}<br>%{y:.1f} MW<br>%{text}<extra></extra>")
    )
    fig.update_layout(
        title="Net delta by interval (colour = recommended side)",
        yaxis_title="MW",
        template="plotly_white",
        height=320,
        margin=dict(l=48, r=16, t=48, b=80),
        xaxis_tickangle=-45,
    )
    return fig


def _cashout_chart(rows: list[list[Any]]) -> go.Figure:
    fig = go.Figure()
    if not rows:
        fig.update_layout(title="Projected cash-out by interval", template="plotly_white", height=280)
        return fig
    xs, ys = [], []
    for row in rows:
        xs.append(str(row[0]))
        try:
            ys.append(float(row[1] or 0))
        except (TypeError, ValueError):
            ys.append(0.0)
    fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines+markers", name="Cash-out €", line=dict(color="#f59e0b")))
    fig.update_layout(
        title="Projected cash-out by interval",
        yaxis_title="€",
        template="plotly_white",
        height=280,
        margin=dict(l=48, r=16, t=48, b=80),
        xaxis_tickangle=-45,
    )
    return fig


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
                                    html.Span("Streaming", className="curve-page-badge"),
                                ],
                            ),
                            ucp.presenter_tip_button("st-near-presenter-tip-btn"),
                        ],
                    ),
                    uicons.hero_title(_PAGE_TITLE, uicons.SHORT_TERM_NAV_ICONS["/short-term/near-delivery"]),
                    html.P(_PAGE_SUMMARY, className="curve-page-summary"),
                ],
            ),
            ucp.presenter_modal(
                _PRESENTER_SECTIONS,
                modal_id="st-near-presenter-modal",
                close_id="st-near-presenter-close",
                backdrop_id="st-near-presenter-backdrop",
                title_id="st-near-presenter-modal-title",
            ),
            html.Div(
                className="curve-callout curve-callout-accent",
                children=html.P(
                    "Sub-second re-forecasts feed squaring recommendations before each cross-border gate closes — "
                    "square the physical delta or face cash-out into delivery.",
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
                                id="st-near-date",
                                options=[],
                                value=None,
                                clearable=False,
                                className="toolbar-select st-toolbar-date",
                                optionHeight=44,
                            ),
                        ],
                    ),
                    html.Div(
                        className="curve-toolbar-field st-toolbar-field-zone",
                        children=[
                            html.Label("Zone", className="curve-toolbar-label"),
                            dcc.Dropdown(
                                id="st-near-zone",
                                options=[{"label": "All zones", "value": "ALL"}],
                                value="ALL",
                                clearable=False,
                                className="toolbar-select st-toolbar-zone",
                                optionHeight=44,
                            ),
                        ],
                    ),
                    html.Button("Refresh", id="st-near-refresh", type="button", className="curve-refresh-btn"),
                ],
            ),
            dcc.Loading(id="st-near-loading", type="default", children=html.Div(id="st-near-body")),
        ],
    )


def _body(warehouse_id: str, delivery_date: str, zone: str) -> html.Div:
    dp = ucp.sql_delivery_date_predicate("delivery_date", delivery_date)
    zone_pred = "" if zone == "ALL" else f" AND zone_code = '{ucp.sql_escape(zone)}'"

    summary_sql = f"""
    SELECT headline, net_open_position_mw, n_intervals_open, n_intervals_closing,
           n_severe_deviations, projected_cashout_eur, system_balance_direction, next_gate_close_ts
    FROM {ucp.fq("short_term_gold_near_delivery_summary")}
    WHERE {dp}
    LIMIT 1
    """
    summary_res = ucp.run_uc_sql(warehouse_id, summary_sql)
    if not summary_res.ok:
        return _alert(f"Could not load desk summary: {summary_res.error}", kind="error")

    parts: list[Any] = []
    if summary_res.rows:
        s = dict(zip(summary_res.columns, summary_res.rows[0]))
        parts.append(
            html.Div(
                className="curve-publication-banner curve-pub-draft",
                children=[
                    html.Span(str(s.get("system_balance_direction") or "—"), className="curve-pub-badge"),
                    html.Span(str(s.get("headline") or ""), className="curve-pub-headline"),
                    html.Span(
                        f"Next gate {s.get('next_gate_close_ts') or '—'} · net open {float(s.get('net_open_position_mw') or 0):.1f} MW",
                        className="curve-pub-meta",
                    ),
                ],
            )
        )
        cashout = float(s.get("projected_cashout_eur") or 0)
        parts.append(html.P(_KPI_LEAD, className="curve-section-lead"))
        parts.append(
            html.Div(
                className="curve-outcome-row",
                children=[
                    _outcome_card("Net open position", f"{float(s.get('net_open_position_mw') or 0):.1f} MW"),
                    _outcome_card("Intervals open", str(int(float(s.get("n_intervals_open") or 0)))),
                    _outcome_card(
                        "Intervals closing",
                        str(int(float(s.get("n_intervals_closing") or 0))),
                        variant="curve-outcome-warn" if float(s.get("n_intervals_closing") or 0) > 0 else "",
                    ),
                    _outcome_card(
                        "Severe deviations",
                        str(int(float(s.get("n_severe_deviations") or 0))),
                        variant="curve-outcome-warn" if float(s.get("n_severe_deviations") or 0) > 0 else "",
                    ),
                    _outcome_card("Projected cash-out", f"€{cashout:,.0f}", variant="curve-outcome-warn" if cashout > 0 else ""),
                ],
            )
        )

    squaring_sql = f"""
    SELECT interval_start, net_delta_mw, recommended_side, gate_status, recommended_mw, expected_price_eur_mwh
    FROM {ucp.fq("short_term_gold_squaring_actions")}
    WHERE {dp}{zone_pred}
    ORDER BY interval_start
    """
    sq_res = ucp.run_uc_sql(warehouse_id, squaring_sql)

    dev_sql = f"""
    SELECT asset_id, interval_start, forecast_mw, prev_forecast_mw, forecast_deviation_mw, deviation_severity
    FROM {ucp.fq("short_term_silver_generation_forecast")}
    WHERE {dp}{zone_pred}
      AND deviation_severity IN ('WATCH', 'SEVERE')
    ORDER BY ABS(forecast_deviation_mw) DESC
    LIMIT 25
    """
    dev_res = ucp.run_uc_sql(warehouse_id, dev_sql)

    imb_sql = f"""
    SELECT interval_start, projected_cashout_eur, net_imbalance_mw, exposure_severity
    FROM {ucp.fq("short_term_gold_imbalance_exposure")}
    WHERE {dp}{zone_pred}
    ORDER BY interval_start
    """
    imb_res = ucp.run_uc_sql(warehouse_id, imb_sql)

    bt_sql = f"""
    SELECT strategy, realized_pnl_eur, cashout_avoided_eur, hit_rate_pct, is_recommended
    FROM {ucp.fq("short_term_gold_backtest_runs")}
    ORDER BY realized_pnl_eur DESC
    """
    bt_res = ucp.run_uc_sql(warehouse_id, bt_sql)

    parts.extend(
        [
            ucp.capability_section(
                "Squaring actions",
                _WIDGET_SQUARING,
                dcc.Graph(
                    figure=_squaring_chart(sq_res.rows if sq_res.ok else []),
                    config={"displayModeBar": False},
                ),
            ),
            ucp.capability_section(
                "Forecast deviations",
                _WIDGET_DEVIATIONS,
                _table(
                    ["Asset", "Interval", "Forecast MW", "Prev MW", "Δ MW", "Severity"],
                    dev_res.rows if dev_res.ok and dev_res.rows else [],
                )
                if dev_res.ok and dev_res.rows
                else html.P("No WATCH or SEVERE deviations on this date.", className="curve-muted"),
            ),
            ucp.capability_section(
                "Imbalance & cash-out",
                _WIDGET_IMBALANCE,
                dcc.Graph(
                    figure=_cashout_chart(imb_res.rows if imb_res.ok else []),
                    config={"displayModeBar": False},
                ),
            ),
            ucp.capability_section(
                "Backtest — prove before live",
                _WIDGET_BACKTEST,
                _table(
                    ["Strategy", "P&L €", "Cash-out avoided €", "Hit rate %", "Recommended"],
                    [
                        [
                            r[0],
                            f"{float(r[1]):,.0f}",
                            f"{float(r[2]):,.0f}",
                            f"{float(r[3]):.1f}",
                            "✓" if str(r[4]).lower() in ("true", "1") else "",
                        ]
                        for r in (bt_res.rows if bt_res.ok else [])
                    ],
                )
                if bt_res.ok and bt_res.rows
                else html.P("No backtest runs seeded.", className="curve-muted"),
            ),
            html.P(f"Snapshot for delivery date {delivery_date}. Illustrative data for demo purposes.", className="curve-footnote"),
        ]
    )
    return html.Div(className="curve-page-body", children=parts)


@callback(
    Output("st-near-date", "options"),
    Output("st-near-date", "value"),
    Output("st-near-zone", "options"),
    Output("st-near-zone", "value"),
    Input("sql-warehouse-dropdown", "value"),
    Input("st-near-refresh", "n_clicks"),
    State("st-near-date", "value"),
    State("st-near-zone", "value"),
    prevent_initial_call=False,
)
def _load_filters(
    warehouse_id: str | None,
    _n: int | None,
    current_date: str | None,
    current_zone: str | None,
):
    zone_opts = [{"label": "All zones", "value": "ALL"}]
    if not warehouse_id:
        return [], None, zone_opts, ucp.resolve_dropdown_value(current_zone, ["ALL"])
    dates_sql = f"""
    SELECT DISTINCT delivery_date FROM {ucp.fq("short_term_dim_intervals")}
    ORDER BY delivery_date DESC LIMIT 30
    """
    zones_sql = f"SELECT zone_code, country FROM {ucp.fq('short_term_dim_zones')} ORDER BY zone_code"
    d_res = ucp.run_uc_sql(warehouse_id, dates_sql)
    z_res = ucp.run_uc_sql(warehouse_id, zones_sql)
    dates = [ucp.normalize_as_of(r[0]) for r in (d_res.rows if d_res.ok else []) if ucp.normalize_as_of(r[0])]
    date_opts = [{"label": d, "value": d} for d in dates]
    if z_res.ok:
        zone_opts += [{"label": f"{r[0]} — {r[1]}", "value": str(r[0])} for r in z_res.rows]
    zone_values = [str(o["value"]) for o in zone_opts]
    return (
        date_opts,
        ucp.resolve_dropdown_value(current_date, dates),
        zone_opts,
        ucp.resolve_dropdown_value(current_zone, zone_values),
    )


@callback(
    Output("st-near-body", "children"),
    Input("sql-warehouse-dropdown", "value"),
    Input("st-near-date", "value"),
    Input("st-near-zone", "value"),
    Input("st-near-refresh", "n_clicks"),
)
def _render_body(warehouse_id: str | None, delivery_date: str | None, zone: str | None, _n: int | None):
    if not warehouse_id:
        return ucp.warehouse_prompt()
    if not delivery_date:
        probe = ucp.run_uc_sql(warehouse_id, f"SELECT COUNT(*) FROM {ucp.fq('short_term_gold_squaring_actions')}")
        if probe.ok and probe.rows and int(float(probe.rows[0][0])) > 0:
            return _alert("Trade dates could not be loaded — choose Refresh.", kind="warn")
        return _alert("No near-delivery data. Run `energy_trading_demo_data`, then select a connection.", kind="warn")
    return _body(warehouse_id, ucp.normalize_as_of(delivery_date) or delivery_date, zone or "ALL")


@callback(
    Output("st-near-presenter-modal", "className"),
    Input("st-near-presenter-tip-btn", "n_clicks"),
    Input("st-near-presenter-close", "n_clicks"),
    Input("st-near-presenter-backdrop", "n_clicks"),
    State("st-near-presenter-modal", "className"),
    prevent_initial_call=True,
)
def _toggle_presenter(_o, _c, _b, current: str | None):
    base = "curve-presenter-modal"
    return base if current and "curve-presenter-modal-open" in current else f"{base} curve-presenter-modal-open"
