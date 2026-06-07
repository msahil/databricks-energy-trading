"""
Forecast Accuracy & Value — score published volume and translate error to euros.
Spec: modules/volume-forecasting/specifications/08-forecast-accuracy-value.md
"""

from __future__ import annotations

from typing import Any

import dash
from dash import Input, Output, State, callback, dcc, html
import plotly.graph_objects as go

import uc_pages as ucp
import ui_icons as uicons

_PATH = "/volume-forecasting/accuracy"

dash.register_page(
    __name__,
    path=_PATH,
    name="Forecast Accuracy & Value",
    title="Forecast Accuracy & Value — Volume forecasting",
)

_PAGE_TITLE = "Forecast Accuracy & Value"
_PAGE_SUMMARY = (
    "Score the published net volume against actuals, attribute error to its source, and translate it "
    "into euros of imbalance cash-out. MAE / RMSE / bias by lead-time and leg, champion / challenger "
    "comparison, and drift alerts — the module's value case."
)

_KPI_LEAD = (
    "How accurate was the official cut, what did error cost, and is any leg drifting?"
)
_WIDGET_LEG = "Where error came from — MAE attributed by forecast leg for the selected filters."
_WIDGET_LEAD = (
    "Accuracy improves as lead time shortens — day-ahead (DA) through real time (RT)."
)
_WIDGET_MODEL = (
    "Champion vs challenger per leg — skill score and promotion candidate flag (MLflow governance story)."
)
_WIDGET_COST = (
    "Cash-out cost of net error over recent delivery days — avoidable vs model-driven share."
)
_WIDGET_DRIFT = "Legs in WATCH or DRIFT — Lakehouse Monitoring style error-distribution alerts."

_LEAD_ORDER = ("DA", "H+4", "H+1", "RT")

_PRESENTER_LEAD = ucp.PRESENTER_LEAD_CAPABILITY

_PRESENTER_SECTIONS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "1 — Pain point for traders",
        (
            "Desk heads hear \"the model is fine\" from quants while imbalance cash-out on the P&L says otherwise. "
            "Without euros on the scoreboard, nobody agrees whether to invest in wind ensembles, meter cleansing, or "
            "solar irradiance — meetings end in opinion, not evidence.",
            "When wind error and consumption error stack on the same delivery day, traders blame the wrong leg because "
            "attribution still lives in separate notebooks and slide decks.",
            "Model drift shows up in money before anyone reruns champion versus challenger. Risk wants an early warning "
            "on the leg that is degrading — not a post-mortem after a bad gate weekend.",
        ),
    ),
    (
        "2 — Business problem this solves",
        (
            "This capability scores the published net volume against actuals — in megawatts and in euros — so management "
            "sees the value of accuracy, not only mean absolute error on a chart.",
            "Error attributed by leg (wind, consumption, solar) directs model spend; the lead-time curve shows where "
            "shorter horizon forecasting helps squaring. Champion versus challenger comparison and drift alerts close "
            "the MLflow governance loop before degradation hits the next publish gate.",
            "When finance is in the room, say: \"A one-point MAE improvement on a book this size is real money — here "
            "is which leg drove yesterday's error and what we do next.\"",
        ),
    ),
    (
        "3 — This page and each widget",
        (
            "Page title and summary: Forecast Accuracy and Value — the module's business case. Show this after "
            "publication so the audience knows you are scoring the official cut, not draft tables.",
            "Toolbar: Delivery date range, zone, and leg filter — narrow to WIND or CONSUMPTION when the room already "
            "debated that leg on prior pages.",
            "Status banner: Net MAE, bias direction, total cash-out cost in euros, and count of legs in DRIFT — the "
            "risk committee scan in one line.",
            "Desk KPI cards: Net MAE percent, bias in megawatts, cash-out euros, and best challenger candidate — "
            "translate model metrics into desk language.",
            "Error by leg chart: Mean absolute error attributed per forecast leg. Ask aloud: \"Was it wind, consumption, "
            "or solar that hurt us yesterday?\" — that directs engineering spend.",
            "Lead-time accuracy chart: Day-ahead through real time — error typically shrinks toward delivery. Use this "
            "to justify investment in short-term consumption and near-delivery squaring.",
            "Champion versus challenger panel: Skill score per leg and promotion candidate flags — the MLflow "
            "governance story for quants and desk heads together.",
            "Cash-out cost strip: Avoidable versus model-driven share over recent delivery days — speak in finance "
            "language traders and executives both respect.",
            "Drift alerts panel: Legs in WATCH or DRIFT — Lakehouse Monitoring style signals to act before the next "
            "official publish, not after imbalance spikes.",
            "Close with conviction: \"We do not ask traders to trust the model on faith — we show what it cost when it "
            "was wrong, which leg to fix, and how the next version is governed.\"",
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


def _acc_pred(zone: str, leg: str, lead: str, *, date_col: str = "delivery_date", delivery_date: str | None = None) -> str:
    parts: list[str] = []
    if delivery_date:
        parts.append(ucp.sql_delivery_date_predicate(date_col, delivery_date))
    if zone and zone != "ALL":
        parts.append(f"zone_code = '{ucp.sql_escape(zone)}'")
    if leg and leg != "ALL":
        parts.append(f"leg = '{ucp.sql_escape(leg)}'")
    if lead and lead != "ALL":
        parts.append(f"lead_bucket = '{ucp.sql_escape(lead)}'")
    return (" AND " + " AND ".join(parts)) if parts else ""


def _lead_sort_key(bucket: str) -> int:
    try:
        return _LEAD_ORDER.index(bucket)
    except ValueError:
        return 99


def _leg_chart(rows: list[list[Any]]) -> go.Figure:
    fig = go.Figure()
    if not rows:
        fig.update_layout(template="plotly_white", height=300, margin=ucp.plotly_chart_margins(n_traces=1))
        return fig

    legs, maes = [str(r[0]) for r in rows], [float(r[1] or 0) for r in rows]
    colors = ["#2563eb" if l == "NET" else "#059669" if l == "WIND" else "#d97706" if l == "SOLAR" else "#7c3aed" for l in legs]
    fig.add_trace(go.Bar(x=legs, y=maes, marker_color=colors, hovertemplate="%{x}<br>MAE %{y:.3f} MW<extra></extra>"))
    fig.update_layout(
        yaxis_title="MAE (MW)",
        template="plotly_white",
        height=300,
        margin=ucp.plotly_chart_margins(n_traces=1),
        showlegend=False,
    )
    return fig


def _lead_chart(rows: list[list[Any]]) -> go.Figure:
    fig = go.Figure()
    if not rows:
        fig.update_layout(template="plotly_white", height=300, margin=ucp.plotly_chart_margins(n_traces=2))
        return fig

    ordered = sorted(rows, key=lambda r: _lead_sort_key(str(r[0])))
    xs = [str(r[0]) for r in ordered]
    mae = [float(r[1] or 0) for r in ordered]
    rmse = [float(r[2] or 0) for r in ordered]

    fig.add_trace(go.Scatter(x=xs, y=mae, name="MAE", line=dict(color="#2563eb", width=2), mode="lines+markers"))
    fig.add_trace(go.Scatter(x=xs, y=rmse, name="RMSE", line=dict(color="#dc2626", width=2, dash="dot"), mode="lines+markers"))
    fig.update_layout(
        yaxis_title="MW",
        template="plotly_white",
        height=300,
        margin=ucp.plotly_chart_margins(n_traces=2),
        legend=ucp.plotly_legend(n_traces=2),
    )
    return fig


def _cost_chart(rows: list[list[Any]]) -> go.Figure:
    fig = go.Figure()
    if not rows:
        fig.update_layout(template="plotly_white", height=280, margin=ucp.plotly_chart_margins(n_traces=2))
        return fig

    xs, cashout, avoidable = [], [], []
    for row in rows:
        xs.append(str(row[0]))
        cashout.append(float(row[1] or 0))
        avoidable.append(float(row[2] or 0))

    fig.add_trace(go.Bar(x=xs, y=cashout, name="Cash-out €", marker_color="#dc2626"))
    fig.add_trace(go.Bar(x=xs, y=avoidable, name="Avoidable €", marker_color="#f59e0b"))
    fig.update_layout(
        barmode="group",
        yaxis_title="€",
        template="plotly_white",
        height=280,
        margin=ucp.plotly_chart_margins(n_traces=2),
        xaxis_tickangle=-45,
        legend=ucp.plotly_legend(n_traces=2),
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
                                    html.Span("Volume forecasting", className="curve-page-eyebrow"),
                                    html.Span("Value case", className="curve-page-badge"),
                                ],
                            ),
                            ucp.presenter_tip_button("vf-acc-presenter-tip-btn"),
                        ],
                    ),
                    uicons.hero_title(_PAGE_TITLE, uicons.VOLUME_FORECAST_NAV_ICONS[_PATH]),
                    html.P(_PAGE_SUMMARY, className="curve-page-summary"),
                ],
            ),
            ucp.presenter_modal(
                _PRESENTER_SECTIONS,
                modal_id="vf-acc-presenter-modal",
                close_id="vf-acc-presenter-close",
                backdrop_id="vf-acc-presenter-backdrop",
                title_id="vf-acc-presenter-modal-title",
                lead=_PRESENTER_LEAD,
            ),
            html.Div(
                className="curve-callout curve-callout-accent",
                children=html.P(
                    "Scores the published net volume (07) against realised legs. "
                    "Error shrinks from day-ahead toward real time — the demo scales residuals by lead bucket.",
                    className="curve-callout-body",
                ),
            ),
            html.Div(
                className="curve-toolbar st-toolbar",
                children=[
                    html.Div(
                        className="curve-toolbar-field st-toolbar-field-date",
                        children=[
                            html.Label("Delivery date", className="curve-toolbar-label"),
                            dcc.Dropdown(
                                id="vf-acc-date",
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
                                id="vf-acc-zone",
                                options=[{"label": "All zones", "value": "ALL"}],
                                value="ALL",
                                clearable=False,
                                className="toolbar-select st-toolbar-zone",
                                optionHeight=44,
                            ),
                        ],
                    ),
                    html.Div(
                        className="curve-toolbar-field st-toolbar-field-zone",
                        children=[
                            html.Label("Leg", className="curve-toolbar-label"),
                            dcc.Dropdown(
                                id="vf-acc-leg",
                                options=[
                                    {"label": "All legs", "value": "ALL"},
                                    {"label": "Net (published)", "value": "NET"},
                                    {"label": "Consumption", "value": "CONSUMPTION"},
                                    {"label": "Industrial", "value": "INDUSTRIAL"},
                                    {"label": "Wind", "value": "WIND"},
                                    {"label": "Solar", "value": "SOLAR"},
                                ],
                                value="NET",
                                clearable=False,
                                className="toolbar-select st-toolbar-zone",
                                optionHeight=44,
                            ),
                        ],
                    ),
                    html.Div(
                        className="curve-toolbar-field st-toolbar-field-zone",
                        children=[
                            html.Label("Lead bucket", className="curve-toolbar-label"),
                            dcc.Dropdown(
                                id="vf-acc-lead",
                                options=[
                                    {"label": "All buckets", "value": "ALL"},
                                    {"label": "Day-ahead (DA)", "value": "DA"},
                                    {"label": "H+4", "value": "H+4"},
                                    {"label": "H+1", "value": "H+1"},
                                    {"label": "Real time (RT)", "value": "RT"},
                                ],
                                value="DA",
                                clearable=False,
                                className="toolbar-select st-toolbar-zone",
                                optionHeight=44,
                            ),
                        ],
                    ),
                    html.Button("Refresh", id="vf-acc-refresh", type="button", className="curve-refresh-btn"),
                ],
            ),
            dcc.Loading(id="vf-acc-loading", type="default", children=html.Div(id="vf-acc-body")),
        ],
    )


def _body(warehouse_id: str, delivery_date: str, zone: str, leg: str, lead: str) -> html.Div:
    filt = _acc_pred(zone, leg, lead, delivery_date=delivery_date)
    leg_chart_filt = _acc_pred(zone, "ALL", lead, delivery_date=delivery_date)
    lead_chart_filt = _acc_pred(zone, leg if leg != "ALL" else "NET", "ALL", delivery_date=delivery_date)

    kpi_sql = f"""
    SELECT
        ROUND(AVG(mae_mw), 3) AS mae_mw,
        ROUND(AVG(rmse_mw), 3) AS rmse_mw,
        ROUND(AVG(bias_mw), 3) AS bias_mw
    FROM {ucp.fq("volume_forecast_gold_accuracy_daily")}
    WHERE {filt.lstrip(" AND ")}
    """
    kpi_res = ucp.run_uc_sql(warehouse_id, kpi_sql)
    if not kpi_res.ok:
        return _alert(f"Could not load accuracy metrics: {kpi_res.error}", kind="error")
    if not kpi_res.rows or kpi_res.rows[0][0] is None:
        return _alert("No accuracy data for this filter.", kind="warn")

    k = dict(zip(kpi_res.columns, kpi_res.rows[0]))
    mae = float(k.get("mae_mw") or 0)
    rmse = float(k.get("rmse_mw") or 0)
    bias = float(k.get("bias_mw") or 0)
    bias_dir = "over-forecast" if bias > 0.05 else "under-forecast" if bias < -0.05 else "neutral"

    cost_filt = _acc_pred(zone, "ALL", lead, delivery_date=delivery_date)
    cost_sql = f"""
    SELECT
        ROUND(SUM(cashout_eur), 0) AS cashout_eur,
        ROUND(SUM(avoidable_eur), 0) AS avoidable_eur,
        ROUND(AVG(value_at_1pct_mae_eur), 0) AS value_1pct
    FROM {ucp.fq("volume_forecast_gold_cost_of_error")}
    WHERE {cost_filt.lstrip(" AND ")}
    """
    cost_res = ucp.run_uc_sql(warehouse_id, cost_sql)
    cashout = 0.0
    avoidable = 0.0
    value_1pct = 0.0
    if cost_res.ok and cost_res.rows:
        c = dict(zip(cost_res.columns, cost_res.rows[0]))
        cashout = float(c.get("cashout_eur") or 0)
        avoidable = float(c.get("avoidable_eur") or 0)
        value_1pct = float(c.get("value_1pct") or 0)

    drift_pred = _acc_pred(zone, leg if leg != "ALL" else "ALL", "ALL", date_col="detected_date", delivery_date=delivery_date)
    drift_sql = f"""
    SELECT MAX(CASE drift_status WHEN 'DRIFT' THEN 3 WHEN 'WATCH' THEN 2 ELSE 1 END) AS drift_rank,
           COUNT(CASE WHEN drift_status IN ('WATCH', 'DRIFT') THEN 1 END) AS n_alerts
    FROM {ucp.fq("volume_forecast_gold_drift_alerts")}
    WHERE {drift_pred.lstrip(" AND ")}
    """
    drift_res = ucp.run_uc_sql(warehouse_id, drift_sql)
    drift_rank = 1
    n_alerts = 0
    if drift_res.ok and drift_res.rows:
        d = dict(zip(drift_res.columns, drift_res.rows[0]))
        drift_rank = int(float(d.get("drift_rank") or 1))
        n_alerts = int(float(d.get("n_alerts") or 0))
    drift_status = "DRIFT" if drift_rank == 3 else "WATCH" if drift_rank == 2 else "STABLE"

    leg_sql = f"""
    SELECT leg, ROUND(AVG(mae_mw), 3)
    FROM {ucp.fq("volume_forecast_gold_accuracy_daily")}
    WHERE {leg_chart_filt.lstrip(" AND ")}
    GROUP BY leg
    ORDER BY leg
    """
    leg_res = ucp.run_uc_sql(warehouse_id, leg_sql)

    lead_sql = f"""
    SELECT lead_bucket, ROUND(AVG(mae_mw), 3), ROUND(AVG(rmse_mw), 3)
    FROM {ucp.fq("volume_forecast_gold_accuracy_daily")}
    WHERE {lead_chart_filt.lstrip(" AND ")}
    GROUP BY lead_bucket
    """
    lead_res = ucp.run_uc_sql(warehouse_id, lead_sql)

    cost_zone_lead = _acc_pred(zone, "ALL", lead)
    cost_trend_sql = f"""
    SELECT delivery_date,
           ROUND(SUM(cashout_eur), 0),
           ROUND(SUM(avoidable_eur), 0)
    FROM {ucp.fq("volume_forecast_gold_cost_of_error")}
    WHERE 1=1{cost_zone_lead}
    GROUP BY delivery_date
    ORDER BY delivery_date
    LIMIT 14
    """
    cost_trend_res = ucp.run_uc_sql(warehouse_id, cost_trend_sql)
    if cost_trend_res.ok and cost_trend_res.rows:
        cost_trend_res.rows.reverse()

    mc_leg = leg if leg != "ALL" else None
    mc_sql = f"""
    SELECT model_id, leg, role, mae_mw, rmse_mw, skill_score, is_promotion_candidate,
           eval_start_date, eval_end_date
    FROM {ucp.fq("volume_forecast_gold_model_comparison")}
    WHERE 1=1{"" if not mc_leg else f" AND leg = '{ucp.sql_escape(mc_leg)}'"}
    ORDER BY leg, role DESC
    """
    mc_res = ucp.run_uc_sql(warehouse_id, mc_sql)

    drift_table_sql = f"""
    SELECT leg, zone_code, metric, drift_status, drift_pct, baseline_value, current_value
    FROM {ucp.fq("volume_forecast_gold_drift_alerts")}
    WHERE {drift_pred.lstrip(" AND ")}
    ORDER BY CASE drift_status WHEN 'DRIFT' THEN 1 WHEN 'WATCH' THEN 2 ELSE 3 END, drift_pct DESC
    """
    drift_table_res = ucp.run_uc_sql(warehouse_id, drift_table_sql)

    banner_cls = "curve-pub-superseded" if drift_status == "DRIFT" else "curve-pub-draft" if drift_status == "WATCH" else "curve-pub-official"
    headline = (
        f"Net error {bias_dir} — MAE {mae:.2f} MW at {lead if lead != 'ALL' else 'all leads'}"
        if leg in ("NET", "ALL")
        else f"{leg} leg — MAE {mae:.2f} MW, bias {bias:+.2f} MW"
    )

    parts: list[Any] = [
        html.Div(
            className=f"curve-publication-banner {banner_cls}",
            children=[
                html.Span(drift_status, className="curve-pub-badge"),
                html.Span(headline, className="curve-pub-headline"),
                html.Span(
                    f"Cash-out €{cashout:,.0f} · avoidable €{avoidable:,.0f} · "
                    f"{n_alerts} drift alert(s) · scored {delivery_date}",
                    className="curve-pub-meta",
                ),
            ],
        ),
        html.P(_KPI_LEAD, className="curve-section-lead"),
        html.Div(
            className="curve-outcome-row",
            children=[
                _outcome_card("MAE", f"{mae:.3f} MW"),
                _outcome_card("RMSE", f"{rmse:.3f} MW", sub=f"bias {bias:+.3f} MW ({bias_dir})"),
                _outcome_card(
                    "Cash-out",
                    f"€{cashout:,.0f}",
                    variant="curve-outcome-warn" if cashout > 5000 else "",
                ),
                _outcome_card(
                    "Value of 1% MAE",
                    f"€{value_1pct:,.0f}",
                    sub="illustrative imbalance price",
                ),
            ],
        ),
        ucp.capability_section(
            "Error by leg",
            _WIDGET_LEG,
            dcc.Graph(
                figure=_leg_chart(leg_res.rows if leg_res.ok else []),
                config={"displayModeBar": False},
            ),
        ),
        ucp.capability_section(
            "Lead-time curve",
            _WIDGET_LEAD,
            dcc.Graph(
                figure=_lead_chart(lead_res.rows if lead_res.ok else []),
                config={"displayModeBar": False},
            ),
        ),
        ucp.capability_section(
            "Champion / challenger",
            _WIDGET_MODEL,
            _table(
                ["Model", "Leg", "Role", "MAE", "RMSE", "Skill", "Promote?", "Eval window"],
                [
                    [
                        r[0], r[1], r[2],
                        f"{float(r[3]):.3f}",
                        f"{float(r[4]):.3f}",
                        f"{float(r[5]):.2f}",
                        "Yes" if str(r[6]).lower() in ("true", "1") else "—",
                        f"{r[7]} → {r[8]}",
                    ]
                    for r in (mc_res.rows if mc_res.ok else [])
                ],
            )
            if mc_res.ok and mc_res.rows
            else html.P("No model comparison rows.", className="curve-muted"),
        ),
        ucp.capability_section(
            "Cost of error",
            _WIDGET_COST,
            dcc.Graph(
                figure=_cost_chart(cost_trend_res.rows if cost_trend_res.ok else []),
                config={"displayModeBar": False},
            ),
        ),
        ucp.capability_section(
            "Drift alerts",
            _WIDGET_DRIFT,
            _table(
                ["Leg", "Zone", "Metric", "Status", "Drift %", "Baseline", "Current"],
                [
                    [r[0], r[1], r[2], r[3], f"{float(r[4]):.1f}%", f"{float(r[5]):.3f}", f"{float(r[6]):.3f}"]
                    for r in (drift_table_res.rows if drift_table_res.ok else [])
                ],
            )
            if drift_table_res.ok and drift_table_res.rows
            else html.P("No drift alerts for this filter.", className="curve-muted"),
        ),
        html.P(f"Accuracy scored for {delivery_date}; published net volume from capability 07.", className="curve-footnote"),
    ]
    return html.Div(className="curve-page-body", children=parts)


@callback(
    Output("vf-acc-date", "options"),
    Output("vf-acc-date", "value"),
    Output("vf-acc-zone", "options"),
    Output("vf-acc-zone", "value"),
    Input("sql-warehouse-dropdown", "value"),
    Input("vf-acc-refresh", "n_clicks"),
    State("vf-acc-date", "value"),
    State("vf-acc-zone", "value"),
    prevent_initial_call=False,
)
def _load_filters(warehouse_id, _n, current_date, current_zone):
    zone_opts = [{"label": "All zones", "value": "ALL"}]
    if not warehouse_id:
        return [], None, zone_opts, "ALL"

    d_res = ucp.run_uc_sql(
        warehouse_id,
        f"""
        SELECT DISTINCT delivery_date
        FROM {ucp.fq("volume_forecast_gold_accuracy_daily")}
        ORDER BY delivery_date DESC
        LIMIT 30
        """,
    )
    z_res = ucp.run_uc_sql(
        warehouse_id,
        f"SELECT zone_code, country FROM {ucp.fq('volume_forecast_dim_zones')} ORDER BY zone_code",
    )

    dates = [ucp.normalize_as_of(r[0]) for r in (d_res.rows if d_res.ok else []) if ucp.normalize_as_of(r[0])]
    if z_res.ok:
        zone_opts += [{"label": f"{r[0]} — {r[1]}", "value": str(r[0])} for r in z_res.rows]

    return (
        [{"label": d, "value": d} for d in dates],
        ucp.resolve_dropdown_value(current_date, dates),
        zone_opts,
        ucp.resolve_dropdown_value(current_zone, [o["value"] for o in zone_opts]),
    )


@callback(
    Output("vf-acc-body", "children"),
    Input("sql-warehouse-dropdown", "value"),
    Input("vf-acc-date", "value"),
    Input("vf-acc-zone", "value"),
    Input("vf-acc-leg", "value"),
    Input("vf-acc-lead", "value"),
    Input("vf-acc-refresh", "n_clicks"),
)
def _render_body(warehouse_id, delivery_date, zone, leg, lead, _n):
    if not warehouse_id:
        return ucp.warehouse_prompt()
    if not delivery_date:
        probe = ucp.run_uc_sql(warehouse_id, f"SELECT COUNT(*) FROM {ucp.fq('volume_forecast_gold_accuracy_daily')}")
        if probe.ok and probe.rows and int(float(probe.rows[0][0])) > 0:
            return _alert("Delivery dates could not be loaded — choose Refresh.", kind="warn")
        return _alert(
            "No accuracy data. Run `energy_trading_demo_data` (needs capability 07 first), then select a connection.",
            kind="warn",
        )
    return _body(
        warehouse_id,
        ucp.normalize_as_of(delivery_date) or delivery_date,
        zone or "ALL",
        leg or "NET",
        lead or "DA",
    )


@callback(
    Output("vf-acc-presenter-modal", "className"),
    Input("vf-acc-presenter-tip-btn", "n_clicks"),
    Input("vf-acc-presenter-close", "n_clicks"),
    Input("vf-acc-presenter-backdrop", "n_clicks"),
    State("vf-acc-presenter-modal", "className"),
    prevent_initial_call=True,
)
def _toggle_presenter(_o, _c, _b, current):
    base = "curve-presenter-modal"
    return base if current and "curve-presenter-modal-open" in current else f"{base} curve-presenter-modal-open"
