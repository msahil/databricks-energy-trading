"""
DSR & Market Access — virtual power plant aggregation desk.
Spec: modules/short-term/specifications/03-dsr-market-access.md
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
    path="/short-term/dsr",
    name="DSR & Market Access",
    title="DSR & Market Access — Short-term trading",
)

_PAGE_TITLE = "DSR & Market Access"
_PAGE_SUMMARY = (
    "Turn distributed flexible assets into a tradable virtual power plant. See fleet-wide flex up/down, "
    "prequalified bid stacks per market, verified dispatch against price and grid signals, and per-owner "
    "settlement ready for Delta Sharing. Midday negative-price absorb and evening scarcity dispatch on "
    "the same fleet — with revenue allocated back to asset owners automatically."
)

_KPI_LEAD = (
    "Fleet headline for the selected day: revenue captured, energy dispatched, delivery quality, and assets online — "
    "the aggregator's single view of whether the VPP is earning or on standby."
)
_WIDGET_AVAILABILITY = (
    "Aggregated flex up and flex down by interval from submeter telemetry and Mosaic AI baselines. "
    "Shows how much volume you can realistically offer into aFRR, mFRR, and Intraday before you bid."
)
_WIDGET_BID_STACK = (
    "Prequalified MW per market against exchange minimum sizes. "
    "Tells the trader which products are bid-ready and at what price band before gate submission."
)
_WIDGET_DISPATCH = (
    "Dispatched and verified MW against price, frequency, or scarcity triggers. "
    "Proves the fleet delivered what it promised — under-delivery flags drive imbalance risk and owner penalties."
)
_WIDGET_SETTLEMENT = (
    "Splits market revenue between asset owners and the aggregator — the Delta Sharing handoff in production. "
    "Owners see what they earned; the desk sees fees retained and settlement status per party."
)

_PRESENTER_SECTIONS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "1 — Pain point for traders",
        (
            "Thousands of industrial sites, EV depots, heat pumps, and behind-the-meter batteries are not on the company's "
            "balance sheet — yet their flexibility can still be traded. Aggregators who confuse third-party flex with "
            "owned generation mis-state the book and mis-bid into balancing products.",
            "In many organisations the VPP desk lives in spreadsheets: availability in one file, prequalified bids in "
            "another, dispatch logs in email, owner settlements at month-end. Under-delivery opens imbalance risk for "
            "the aggregator and destroys trust with asset owners who expect transparent, timely statements.",
            "The same fleet must flex down into midday negative prices and flex up into evening scarcity — often on the "
            "same delivery day. Traders need proof of what was available, what was bid, what actually dispatched, and "
            "what owners earned before the control tower asks why the balance ribbon moved.",
        ),
    ),
    (
        "2 — Business problem this solves",
        (
            "This page is the virtual power plant desk end to end: fleet availability by interval, a prequalified bid "
            "stack by product, verified dispatch events, and owner settlement — all on governed tables, not shadow "
            "spreadsheets.",
            "Verified flex dispatch feeds the operations control tower balance ribbon beside owned-asset squaring. "
            "Near-delivery squares what the company owns; this screen monetises flexibility the desk manages "
            "commercially but does not physically operate. Together they are how modern desks survive volatile "
            "quarter-hours.",
            "Walk a day-in-the-life arc traders recognise: morning — \"how much flex up and down do we have?\"; before "
            "gate — \"what is bid-ready at what price?\"; midday — negative-price absorb; evening — scarcity dispatch "
            "into balancing; end of day — settlement and margin. Then open the control tower and point at flex contribution.",
        ),
    ),
    (
        "3 — This page and each widget",
        (
            "Page title and summary: Open on DSR and Market Access. Explain in one sentence that this is aggregated "
            "third-party flex — bid into wholesale and balancing products, verify metered delivery, pay owners fairly.",
            "Toolbar: Keep trade date aligned with near-delivery and the control tower. The market filter slices aFRR, "
            "mFRR, intraday, or all products — useful when someone in the room only trades one balancing product. "
            "Refresh when numbers look stale; aggregators refresh often in live operations.",
            "Fleet banner: Stress this is the aggregated portfolio, not owned megawatts — traders should not confuse it "
            "with the generation stack on the control tower. Read the headline as the commercial story of the day "
            "(negative-price absorb window, evening scarcity, and so on). Call out peak flex up and flex down in the "
            "meta line — that is the headline capacity you can bid before drilling into intervals.",
            "Fleet KPI cards: Market revenue — \"what we captured before sharing with owners.\" Owner payments — "
            "\"what leaves the aggregator's pocket — transparency matters in VPP relationships.\" Dispatched energy — "
            "\"what actually moved in verified events, not what we hoped.\" Delivery ratio — under-delivery hurts "
            "everyone. Assets online — a thin fleet means thinner bids; say that plainly if the number looks low.",
            "Availability chart: Flex up and flex down by interval — the physical ceiling on what you can offer. State "
            "the rule traders respect: never bid more than the fleet can deliver. A midday peak in flex down tees up the "
            "negative-price absorb story before you scroll to dispatch.",
            "Prequalified bid stack table: \"What we are allowed and willing to bid, by product\" — qualified megawatts, "
            "price, status. TSO rules on minimum size and response time are already baked into qualified volume. Use the "
            "market filter to separate balancing from intraday if needed.",
            "Dispatch and verification table: Walk one row slowly — trigger (negative price, scarcity, frequency), "
            "requested MW, delivered MW, verification status. Verified protects revenue; under-delivered opens imbalance "
            "and owner penalty conversations. Link triggers back to grid frequency on the control tower or price shape "
            "on near-delivery.",
            "Owner settlement table: The commercial close — per-owner energy, revenue, payment, aggregator fee, status. "
            "Owners expect a governed statement, not a CSV at month-end. Revenue minus owner payment is aggregator margin.",
            "Close with conviction: \"Flex is a traded product here — availability, bid, verify, pay — on the same "
            "lakehouse the operator sees when flex moves the balance ribbon.\"",
        ),
    ),
)

_DSR_MARKET_OPTS = [
    {"label": "All markets", "value": "ALL"},
    {"label": "aFRR", "value": "AFRR"},
    {"label": "mFRR", "value": "MFRR"},
    {"label": "Intraday", "value": "INTRADAY"},
]
_DSR_MARKET_VALUES = [str(o["value"]) for o in _DSR_MARKET_OPTS]


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


def _availability_chart(rows: list[list[Any]]) -> go.Figure:
    fig = go.Figure()
    if not rows:
        fig.update_layout(title="Fleet availability by interval", template="plotly_white", height=300)
        return fig
    xs = [str(r[0]) for r in rows]
    up = [float(r[1] or 0) for r in rows]
    down = [float(r[2] or 0) for r in rows]
    fig.add_trace(go.Bar(x=xs, y=up, name="Flex up MW", marker_color="#22c55e"))
    fig.add_trace(go.Bar(x=xs, y=down, name="Flex down MW", marker_color="#3b82f6"))
    fig.update_layout(
        title="Aggregated availability by interval",
        barmode="group",
        yaxis_title="MW",
        template="plotly_white",
        height=300,
        margin=dict(l=48, r=16, t=48, b=80),
        xaxis_tickangle=-45,
        legend=dict(orientation="h", y=1.12),
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
                                    html.Span("VPP", className="curve-page-badge"),
                                    html.Span("Delta Sharing", className="curve-page-badge"),
                                ],
                            ),
                            ucp.presenter_tip_button("st-dsr-presenter-tip-btn"),
                        ],
                    ),
                    uicons.hero_title(_PAGE_TITLE, uicons.SHORT_TERM_NAV_ICONS["/short-term/dsr"]),
                    html.P(_PAGE_SUMMARY, className="curve-page-summary"),
                ],
            ),
            ucp.presenter_modal(
                _PRESENTER_SECTIONS,
                modal_id="st-dsr-presenter-modal",
                close_id="st-dsr-presenter-close",
                backdrop_id="st-dsr-presenter-backdrop",
                title_id="st-dsr-presenter-modal-title",
            ),
            html.Div(
                className="curve-callout curve-callout-accent",
                children=html.P(
                    "Aggregate thousands of industrial loads, EV depots, heat pumps, and batteries into one tradable VPP — "
                    "bid, dispatch, verify, and settle without leaving the desk.",
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
                                id="st-dsr-date",
                                options=[],
                                value=None,
                                clearable=False,
                                className="toolbar-select st-toolbar-date",
                                optionHeight=44,
                            ),
                        ],
                    ),
                    html.Div(
                        className="curve-toolbar-field st-toolbar-field-market",
                        children=[
                            html.Label("Market", className="curve-toolbar-label"),
                            dcc.Dropdown(
                                id="st-dsr-market",
                                options=_DSR_MARKET_OPTS,
                                value="ALL",
                                clearable=False,
                                className="toolbar-select st-toolbar-market",
                                optionHeight=44,
                            ),
                        ],
                    ),
                    html.Button("Refresh", id="st-dsr-refresh", type="button", className="curve-refresh-btn"),
                ],
            ),
            dcc.Loading(id="st-dsr-loading", type="default", children=html.Div(id="st-dsr-body")),
        ],
    )


def _body(warehouse_id: str, delivery_date: str, market: str) -> html.Div:
    dp = ucp.sql_delivery_date_predicate("delivery_date", delivery_date)
    m_pred = "" if market == "ALL" else f" AND market = '{ucp.sql_escape(market)}'"

    sum_sql = f"""
    SELECT headline, total_available_up_mw, total_available_down_mw, total_dispatched_mwh,
           total_market_revenue_eur, total_owner_payments_eur, avg_delivery_ratio, n_assets_online
    FROM {ucp.fq("short_term_gold_dsr_summary")}
    WHERE {dp}
    LIMIT 1
    """
    sum_res = ucp.run_uc_sql(warehouse_id, sum_sql)
    if not sum_res.ok:
        return _alert(sum_res.error or "Summary load failed", kind="error")

    parts: list[Any] = []
    if sum_res.rows:
        s = dict(zip(sum_res.columns, sum_res.rows[0]))
        parts.append(
            html.Div(
                className="curve-publication-banner curve-pub-official",
                children=[
                    html.Span("VPP", className="curve-pub-badge"),
                    html.Span(str(s.get("headline") or ""), className="curve-pub-headline"),
                    html.Span(
                        f"Flex up {float(s.get('total_available_up_mw') or 0):.0f} MW · "
                        f"down {float(s.get('total_available_down_mw') or 0):.0f} MW",
                        className="curve-pub-meta",
                    ),
                ],
            )
        )
        parts.append(html.P(_KPI_LEAD, className="curve-section-lead"))
        parts.append(
            html.Div(
                className="curve-outcome-row",
                children=[
                    _outcome_card("Market revenue", f"€{float(s.get('total_market_revenue_eur') or 0):,.0f}"),
                    _outcome_card("Owner payments", f"€{float(s.get('total_owner_payments_eur') or 0):,.0f}"),
                    _outcome_card("Dispatched", f"{float(s.get('total_dispatched_mwh') or 0):.1f} MWh"),
                    _outcome_card("Delivery ratio", f"{float(s.get('avg_delivery_ratio') or 0):.0%}"),
                    _outcome_card("Assets online", str(int(float(s.get("n_assets_online") or 0)))),
                ],
            )
        )

    avail_sql = f"""
    SELECT interval_start, SUM(available_up_mw), SUM(available_down_mw)
    FROM {ucp.fq("short_term_silver_dsr_availability")}
    WHERE {dp}
    GROUP BY interval_start
    ORDER BY interval_start
    """
    bid_sql = f"""
    SELECT market, SUM(qualified_mw), AVG(bid_price_eur_mwh), MAX(prequalification_status)
    FROM {ucp.fq("short_term_gold_dsr_bid_stack")}
    WHERE {dp}{m_pred}
    GROUP BY market
    ORDER BY market
    """
    disp_sql = f"""
    SELECT interval_start, market, signal_trigger, dispatched_mw, delivered_mw, delivery_ratio, verification_status
    FROM {ucp.fq("short_term_gold_dsr_dispatch")}
    WHERE {dp}{m_pred}
    ORDER BY interval_start
    """
    set_sql = f"""
    SELECT owner_name, total_delivered_mwh, market_revenue_eur, owner_payment_eur, aggregator_fee_eur, settlement_status
    FROM {ucp.fq("short_term_gold_dsr_settlement")}
    WHERE {dp}
    ORDER BY market_revenue_eur DESC
    """

    avail_res = ucp.run_uc_sql(warehouse_id, avail_sql)
    bid_res = ucp.run_uc_sql(warehouse_id, bid_sql)
    disp_res = ucp.run_uc_sql(warehouse_id, disp_sql)
    set_res = ucp.run_uc_sql(warehouse_id, set_sql)

    parts.extend(
        [
            ucp.capability_section(
                "Availability",
                _WIDGET_AVAILABILITY,
                dcc.Graph(figure=_availability_chart(avail_res.rows if avail_res.ok else []), config={"displayModeBar": False}),
            ),
            ucp.capability_section(
                "Prequalified bid stack",
                _WIDGET_BID_STACK,
                _table(
                    ["Market", "Qualified MW", "Bid €/MWh", "Status"],
                    [
                        [r[0], f"{float(r[1]):.1f}", f"{float(r[2]):.2f}", r[3]]
                        for r in (bid_res.rows if bid_res.ok else [])
                    ],
                )
                if bid_res.ok and bid_res.rows
                else html.P("No bid-stack rows for this filter.", className="curve-muted"),
            ),
            ucp.capability_section(
                "Dispatch & verification",
                _WIDGET_DISPATCH,
                _table(
                    ["Interval", "Market", "Trigger", "Dispatched MW", "Delivered MW", "Ratio", "Status"],
                    disp_res.rows if disp_res.ok and disp_res.rows else [],
                )
                if disp_res.ok and disp_res.rows
                else html.P("No dispatch events on this date.", className="curve-muted"),
            ),
            ucp.capability_section(
                "Owner settlement (Delta Sharing)",
                _WIDGET_SETTLEMENT,
                _table(
                    ["Owner", "MWh", "Revenue €", "Owner €", "Fee €", "Status"],
                    [
                        [r[0], f"{float(r[1]):.2f}", f"{float(r[2]):,.0f}", f"{float(r[3]):,.0f}", f"{float(r[4]):,.0f}", r[5]]
                        for r in (set_res.rows if set_res.ok else [])
                    ],
                )
                if set_res.ok and set_res.rows
                else html.P("No settlement rows.", className="curve-muted"),
            ),
            html.P(f"Snapshot for delivery date {delivery_date}. Illustrative VPP data.", className="curve-footnote"),
        ]
    )
    return html.Div(className="curve-page-body", children=parts)


@callback(
    Output("st-dsr-date", "options"),
    Output("st-dsr-date", "value"),
    Output("st-dsr-market", "value"),
    Input("sql-warehouse-dropdown", "value"),
    Input("st-dsr-refresh", "n_clicks"),
    State("st-dsr-date", "value"),
    State("st-dsr-market", "value"),
    prevent_initial_call=False,
)
def _load_dates(
    warehouse_id: str | None,
    _n: int | None,
    current_date: str | None,
    current_market: str | None,
):
    market_val = ucp.resolve_dropdown_value(current_market, _DSR_MARKET_VALUES)
    if not warehouse_id:
        return [], None, market_val
    sql = f"""
    SELECT DISTINCT delivery_date FROM {ucp.fq("short_term_dim_intervals")}
    ORDER BY delivery_date DESC LIMIT 30
    """
    res = ucp.run_uc_sql(warehouse_id, sql)
    dates = [ucp.normalize_as_of(r[0]) for r in (res.rows if res.ok else []) if ucp.normalize_as_of(r[0])]
    opts = [{"label": d, "value": d} for d in dates]
    return opts, ucp.resolve_dropdown_value(current_date, dates), market_val


@callback(
    Output("st-dsr-body", "children"),
    Input("sql-warehouse-dropdown", "value"),
    Input("st-dsr-date", "value"),
    Input("st-dsr-market", "value"),
    Input("st-dsr-refresh", "n_clicks"),
)
def _render(warehouse_id: str | None, delivery_date: str | None, market: str | None, _n: int | None):
    if not warehouse_id:
        return ucp.warehouse_prompt()
    if not delivery_date:
        return _alert("No DSR data. Run `energy_trading_demo_data` (notebooks 01 → 03 → 02).", kind="warn")
    return _body(warehouse_id, ucp.normalize_as_of(delivery_date) or delivery_date, market or "ALL")


@callback(
    Output("st-dsr-presenter-modal", "className"),
    Input("st-dsr-presenter-tip-btn", "n_clicks"),
    Input("st-dsr-presenter-close", "n_clicks"),
    Input("st-dsr-presenter-backdrop", "n_clicks"),
    State("st-dsr-presenter-modal", "className"),
    prevent_initial_call=True,
)
def _toggle_presenter(_o, _c, _b, current: str | None):
    base = "curve-presenter-modal"
    return base if current and "curve-presenter-modal-open" in current else f"{base} curve-presenter-modal-open"
