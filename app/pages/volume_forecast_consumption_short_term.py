"""
Customer Consumption — Short Term — probabilistic demand for the prompt desk.
Spec: modules/volume-forecasting/specifications/01-customer-consumption-short-term.md
"""

from __future__ import annotations

from typing import Any

import dash
from dash import Input, Output, State, callback, dcc, html
import plotly.graph_objects as go

import uc_pages as ucp
import ui_icons as uicons

_PATH = "/volume-forecasting/consumption-short-term"

dash.register_page(
    __name__,
    path=_PATH,
    name="Customer Consumption — Short Term",
    title="Consumption · Short Term — Volume forecasting",
)

_PAGE_TITLE = "Customer Consumption — Short Term"
_PAGE_SUMMARY = (
    "Forecast retail and C&I demand from now through the next several days at 15-minute grain. "
    "Weather shapes the profile anchored on curated metering; P50 is what the prompt desk squares "
    "against, and the P10–P90 band sizes the risk."
)

_KPI_LEAD = (
    "Desk snapshot for the selected day: daily energy at P50, peak demand, uncertainty band, "
    "and how far the latest forecast run moved versus the previous one."
)
_WIDGET_FAN = (
    "Probabilistic demand fan — P10 / P50 / P90 around the median forecast. "
    "Realised actuals overlay up to \"now\" on settled intervals."
)
_WIDGET_SEGMENT = (
    "Which customer segments drive load at P50 — residential peaks vs industrial baseload."
)
_WIDGET_MOVE = (
    "How the forecast moved since the previous run (latest vintage minus prior P50). "
    "Large moves often follow a weather refresh."
)

_PRESENTER_LEAD = ucp.PRESENTER_LEAD_CAPABILITY

_PRESENTER_SECTIONS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "1 — Pain point for traders",
        (
            "Before the prompt desk can square the book, it must know how much customers will draw — but short-term "
            "demand moves with temperature, wind chill, cloud-driven behaviour, and whether it is a weekday or holiday. "
            "That move often happens after the morning hedge was set.",
            "A wrong demand forecast does not stay in the forecasting team. It poisons net position, nominations, and "
            "imbalance cash-out for every quarter-hour that follows. Traders feel demand error as open position, not as "
            "a model metric on someone else's dashboard.",
            "What the desk needs is the shape of the day and an honest uncertainty band — not a single megawatt number "
            "from a spreadsheet whose meter profile nobody has audited.",
        ),
    ),
    (
        "2 — Business problem this solves",
        (
            "Short-term consumption layers weather on top of the curated net-load profile from Smart Metering. Demand "
            "is governed and meter-grounded, not guessed from last year's calendar.",
            "P50 is the demand leg that publication reconciles into official net volume; P10 through P90 sizes risk for "
            "schedulers and risk teams before gate close. The forecast-move strip shows when the latest weather run "
            "shifted the number — the same physical story near-delivery surfaces as severe deviations on assets.",
            "When you need a line that ties the module together, say: \"Demand is the other side of the wind story — "
            "both legs reconcile in publication before the squaring desk acts on one official net MW.\"",
        ),
    ),
    (
        "3 — This page and each widget",
        (
            "Page title and summary: Customer Consumption — Short Term. Explain that this is weather-driven probabilistic "
            "demand at fifteen-minute grain, built on trusted meter shapes from capability four.",
            "Toolbar: Point at delivery date, zone, and segment filters. Keep the date aligned with wind, solar, and "
            "publication so the demo tells one story. Segment lets you drill residential, SME, or industrial — useful "
            "when the room asks who is driving the evening peak.",
            "Status banner: Read the day headline, peak interval, and band width like a scheduling note a shift lead "
            "would use. This sets the weather-and-load story before you open charts.",
            "Desk KPI cards: Day total P50 answers \"how much load today?\" Peak MW answers \"when does it hurt most?\" "
            "Band width answers \"how uncertain is weather?\" Segments in WATCH flag where the model is nervous — say "
            "you would look there before squaring.",
            "Consumption fan chart: Walk the P10, P50, and P90 lines interval by interval. The shaded band is weather "
            "risk, not cosmetic shading. On residential-heavy days, point at the evening peak and say that is what "
            "schedulers nominate against.",
            "Segment breakdown chart: Show which customer class drives the peak — residential evening lift versus SME "
            "daytime flatness. One sentence for executives: \"We forecast at segment grain, then roll up for "
            "publication and squaring.\"",
            "Forecast move chart: Describe this as what the latest weather run did versus the previous vintage. Large "
            "moves here are why the prompt desk re-squares — tee up near-delivery if you are continuing the short-term "
            "module after volume forecasting.",
            "Close with conviction: \"This demand leg is meter-grounded and weather-aware — publication turns it into "
            "the official number every trader squares, not a draft in someone's inbox.\"",
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


def _opt_float(value: Any) -> float | None:
    """Parse warehouse cells that may be null, empty, or the string 'null'."""
    if value is None:
        return None
    s = str(value).strip()
    if not s or s.lower() in ("none", "null", "nan"):
        return None
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def _zone_segment_pred(zone: str, segment: str) -> str:
    parts: list[str] = []
    if zone and zone != "ALL":
        parts.append(f"zone_code = '{ucp.sql_escape(zone)}'")
    if segment and segment != "ALL":
        parts.append(f"segment_code = '{ucp.sql_escape(segment)}'")
    return (" AND " + " AND ".join(parts)) if parts else ""


def _latest_vintage_cte(delivery_date: str, extra_pred: str) -> str:
    dp = ucp.sql_delivery_date_predicate("delivery_date", delivery_date)
    return f"""
    latest_vintage AS (
        SELECT MAX(forecast_ts) AS forecast_ts
        FROM {ucp.fq("volume_forecast_silver_consumption_st")}
        WHERE {dp}{extra_pred}
    )
    """


def _fan_chart(rows: list[list[Any]]) -> go.Figure:
    """P10/P50/P90 ribbon with realised actuals."""
    fig = go.Figure()
    if not rows:
        fig.update_layout(template="plotly_white", height=360, margin=ucp.plotly_chart_margins(n_traces=4))
        return fig

    xs, p10, p50, p90, actual = [], [], [], [], []
    for row in rows:
        xs.append(str(row[0]))
        p10.append(float(row[1] or 0))
        p50.append(float(row[2] or 0))
        p90.append(float(row[3] or 0))
        actual.append(_opt_float(row[4]))

    fig.add_trace(
        go.Scatter(
            x=xs + xs[::-1],
            y=p90 + p10[::-1],
            fill="toself",
            fillcolor="rgba(37, 99, 235, 0.15)",
            line=dict(color="rgba(255,255,255,0)"),
            name="P10–P90 band",
            hoverinfo="skip",
        )
    )
    fig.add_trace(go.Scatter(x=xs, y=p50, name="P50", line=dict(color="#2563eb", width=2)))
    if any(v is not None for v in actual):
        fig.add_trace(
            go.Scatter(
                x=xs,
                y=[v if v is not None else None for v in actual],
                name="Actual",
                line=dict(color="#16a34a", width=2, dash="dot"),
                mode="lines+markers",
                marker=dict(size=4),
            )
        )
    n_traces = 3 if any(v is not None for v in actual) else 2
    fig.update_layout(
        yaxis_title="MW",
        template="plotly_white",
        height=360,
        margin=ucp.plotly_chart_margins(n_traces=n_traces),
        xaxis_tickangle=-45,
        legend=ucp.plotly_legend(n_traces=n_traces),
    )
    return fig


def _segment_chart(rows: list[list[Any]]) -> go.Figure:
    """Stacked P50 by segment over the day."""
    fig = go.Figure()
    if not rows:
        fig.update_layout(template="plotly_white", height=320, margin=ucp.plotly_chart_margins(n_traces=5))
        return fig

    by_segment: dict[str, list[tuple[str, float]]] = {}
    for row in rows:
        interval, segment, p50 = str(row[0]), str(row[1]), float(row[2] or 0)
        by_segment.setdefault(segment, []).append((interval, p50))

    palette = ["#2563eb", "#7c3aed", "#db2777", "#ea580c", "#16a34a"]
    for i, (seg, points) in enumerate(sorted(by_segment.items())):
        points.sort(key=lambda p: p[0])
        fig.add_trace(
            go.Scatter(
                x=[p[0] for p in points],
                y=[p[1] for p in points],
                name=seg,
                stackgroup="one",
                mode="lines",
                line=dict(width=0.5, color=palette[i % len(palette)]),
                fillcolor=palette[i % len(palette)],
            )
        )
    n_traces = len(by_segment)
    fig.update_layout(
        yaxis_title="MW",
        template="plotly_white",
        height=320,
        margin=ucp.plotly_chart_margins(n_traces=n_traces),
        xaxis_tickangle=-45,
        legend=ucp.plotly_legend(n_traces=n_traces),
    )
    return fig


def _move_chart(rows: list[list[Any]]) -> go.Figure:
    """Forecast delta since previous run."""
    fig = go.Figure()
    if not rows:
        fig.update_layout(template="plotly_white", height=260, margin=ucp.plotly_chart_margins(n_traces=1))
        return fig

    xs, ys, colors = [], [], []
    for row in rows:
        xs.append(str(row[0]))
        delta = float(row[1] or 0)
        ys.append(delta)
        colors.append("#22c55e" if delta >= 0 else "#ef4444")
    fig.add_trace(
        go.Bar(
            x=xs,
            y=ys,
            marker_color=colors,
            name="Forecast Δ",
            hovertemplate="%{x}<br>Δ %{y:.2f} MW<extra></extra>",
        )
    )
    fig.update_layout(
        yaxis_title="Δ MW",
        template="plotly_white",
        height=260,
        margin=ucp.plotly_chart_margins(n_traces=1),
        xaxis_tickangle=-45,
        showlegend=False,
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
                                    html.Span("Prompt desk", className="curve-page-badge"),
                                ],
                            ),
                            ucp.presenter_tip_button("vf-st-presenter-tip-btn"),
                        ],
                    ),
                    uicons.hero_title(_PAGE_TITLE, uicons.VOLUME_FORECAST_NAV_ICONS[_PATH]),
                    html.P(_PAGE_SUMMARY, className="curve-page-summary"),
                ],
            ),
            ucp.presenter_modal(
                _PRESENTER_SECTIONS,
                modal_id="vf-st-presenter-modal",
                close_id="vf-st-presenter-close",
                backdrop_id="vf-st-presenter-backdrop",
                title_id="vf-st-presenter-modal-title",
                lead=_PRESENTER_LEAD,
            ),
            html.Div(
                className="curve-callout curve-callout-accent",
                children=html.P(
                    "P50 is the squaring reference; the band sizes risk. Latest forecast vintage only — "
                    "two runs per interval support the move strip and accuracy backtesting.",
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
                                id="vf-st-date",
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
                                id="vf-st-zone",
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
                            html.Label("Segment", className="curve-toolbar-label"),
                            dcc.Dropdown(
                                id="vf-st-segment",
                                options=[{"label": "All segments", "value": "ALL"}],
                                value="ALL",
                                clearable=False,
                                className="toolbar-select st-toolbar-zone",
                                optionHeight=44,
                            ),
                        ],
                    ),
                    html.Button("Refresh", id="vf-st-refresh", type="button", className="curve-refresh-btn"),
                ],
            ),
            dcc.Loading(id="vf-st-loading", type="default", children=html.Div(id="vf-st-body")),
        ],
    )


def _body(warehouse_id: str, delivery_date: str, zone: str, segment: str) -> html.Div:
    dp = ucp.sql_delivery_date_predicate("delivery_date", delivery_date)
    filt = _zone_segment_pred(zone, segment)
    zone_only = _zone_segment_pred(zone, "ALL")

    if zone != "ALL":
        summary_sql = f"""
        SELECT headline, total_demand_mwh, avg_demand_mw, peak_mw, peak_interval,
               band_width_mw, dq_status, snapshot_ts
        FROM {ucp.fq("volume_forecast_gold_consumption_st_summary")}
        WHERE {dp} AND zone_code = '{ucp.sql_escape(zone)}'
        LIMIT 1
        """
    else:
        summary_sql = f"""
        SELECT
            MAX(headline) AS headline,
            ROUND(SUM(total_demand_mwh), 1) AS total_demand_mwh,
            ROUND(AVG(avg_demand_mw), 1) AS avg_demand_mw,
            ROUND(MAX(peak_mw), 1) AS peak_mw,
            MAX(peak_interval) AS peak_interval,
            ROUND(AVG(band_width_mw), 1) AS band_width_mw,
            MAX(CASE dq_status WHEN 'SUSPECT' THEN 3 WHEN 'IMPUTED' THEN 2 ELSE 1 END) AS dq_rank,
            MAX(snapshot_ts) AS snapshot_ts
        FROM {ucp.fq("volume_forecast_gold_consumption_st_summary")}
        WHERE {dp}
        """
    sum_res = ucp.run_uc_sql(warehouse_id, summary_sql)
    if not sum_res.ok:
        return _alert(f"Could not load consumption summary: {sum_res.error}", kind="error")
    if not sum_res.rows:
        return _alert("No consumption summary for this filter.", kind="warn")

    s = dict(zip(sum_res.columns, sum_res.rows[0]))
    if zone == "ALL":
        dq_rank = int(float(s.get("dq_rank") or 1))
        dq_status = "SUSPECT" if dq_rank == 3 else "IMPUTED" if dq_rank == 2 else "GOOD"
    else:
        dq_status = str(s.get("dq_status") or "GOOD")

    total_mwh = float(s.get("total_demand_mwh") or 0)
    peak_mw = float(s.get("peak_mw") or 0)
    band = float(s.get("band_width_mw") or 0)
    peak_interval = str(s.get("peak_interval") or "—")
    headline = str(s.get("headline") or "Demand forecast loaded")
    snapshot_ts = str(s.get("snapshot_ts") or "—")

    cte = _latest_vintage_cte(delivery_date, zone_only if segment == "ALL" else filt)
    move_sql = f"""
    WITH {cte}
    SELECT
        ROUND(MAX(ABS(forecast_delta_mw)), 2) AS peak_move,
        ROUND(AVG(ABS(forecast_delta_mw)), 2) AS avg_move
    FROM {ucp.fq("volume_forecast_silver_consumption_st")} c
    INNER JOIN latest_vintage v ON c.forecast_ts = v.forecast_ts
    WHERE {dp}{zone_only if segment == "ALL" else filt}
      AND forecast_delta_mw IS NOT NULL
    """
    move_kpi_res = ucp.run_uc_sql(warehouse_id, move_sql)
    peak_move = 0.0
    avg_move = 0.0
    if move_kpi_res.ok and move_kpi_res.rows:
        m = dict(zip(move_kpi_res.columns, move_kpi_res.rows[0]))
        peak_move = float(m.get("peak_move") or 0)
        avg_move = float(m.get("avg_move") or 0)

    fan_sql = f"""
    WITH {cte}
    SELECT interval_start,
           ROUND(SUM(p10_mw), 2), ROUND(SUM(p50_mw), 2), ROUND(SUM(p90_mw), 2),
           ROUND(SUM(actual_mw), 2)
    FROM {ucp.fq("volume_forecast_silver_consumption_st")} c
    INNER JOIN latest_vintage v ON c.forecast_ts = v.forecast_ts
    WHERE {dp}{zone_only if segment == "ALL" else filt}
    GROUP BY interval_start
    ORDER BY interval_start
    """
    fan_res = ucp.run_uc_sql(warehouse_id, fan_sql)

    seg_sql = f"""
    WITH {cte}
    SELECT interval_start, segment_code, ROUND(SUM(p50_mw), 2)
    FROM {ucp.fq("volume_forecast_silver_consumption_st")} c
    INNER JOIN latest_vintage v ON c.forecast_ts = v.forecast_ts
    WHERE {dp}{zone_only}
    GROUP BY interval_start, segment_code
    ORDER BY interval_start, segment_code
    """
    seg_res = ucp.run_uc_sql(warehouse_id, seg_sql)

    delta_sql = f"""
    WITH {cte}
    SELECT interval_start, ROUND(SUM(forecast_delta_mw), 2)
    FROM {ucp.fq("volume_forecast_silver_consumption_st")} c
    INNER JOIN latest_vintage v ON c.forecast_ts = v.forecast_ts
    WHERE {dp}{zone_only if segment == "ALL" else filt}
      AND forecast_delta_mw IS NOT NULL
    GROUP BY interval_start
    ORDER BY interval_start
    """
    delta_res = ucp.run_uc_sql(warehouse_id, delta_sql)

    banner_variant = "curve-pub-draft" if dq_status == "GOOD" else "curve-pub-superseded"
    parts: list[Any] = [
        html.Div(
            className=f"curve-publication-banner {banner_variant}",
            children=[
                html.Span(dq_status, className="curve-pub-badge"),
                html.Span(headline, className="curve-pub-headline"),
                html.Span(
                    f"Peak {peak_mw:.1f} MW at {peak_interval} · band {band:.1f} MW · "
                    f"as of {snapshot_ts}",
                    className="curve-pub-meta",
                ),
            ],
        ),
        html.P(_KPI_LEAD, className="curve-section-lead"),
        html.Div(
            className="curve-outcome-row",
            children=[
                _outcome_card("Daily energy (P50)", f"{total_mwh:,.1f} MWh"),
                _outcome_card("Peak demand", f"{peak_mw:.1f} MW", sub=f"at {peak_interval}"),
                _outcome_card(
                    "Uncertainty band",
                    f"{band:.1f} MW",
                    variant="curve-outcome-warn" if band > 40 else "",
                ),
                _outcome_card(
                    "Forecast move",
                    f"±{peak_move:.2f} MW",
                    sub=f"avg |Δ| {avg_move:.2f} MW",
                    variant="curve-outcome-warn" if peak_move > 5 else "",
                ),
            ],
        ),
        ucp.capability_section(
            "Demand fan",
            _WIDGET_FAN,
            dcc.Graph(
                figure=_fan_chart(fan_res.rows if fan_res.ok else []),
                config={"displayModeBar": False},
            ),
        ),
        ucp.capability_section(
            "Segment breakdown",
            _WIDGET_SEGMENT,
            dcc.Graph(
                figure=_segment_chart(seg_res.rows if seg_res.ok else []),
                config={"displayModeBar": False},
            )
            if segment == "ALL"
            else html.P(
                f"Segment filter set to {segment} — open All segments to see the stacked breakdown.",
                className="curve-muted",
            ),
        ),
        ucp.capability_section(
            "Forecast move",
            _WIDGET_MOVE,
            dcc.Graph(
                figure=_move_chart(delta_res.rows if delta_res.ok else []),
                config={"displayModeBar": False},
            ),
        ),
        html.P(
            f"Snapshot for {delivery_date}; latest forecast vintage. "
            "Anchored on curated meter profile (capability 04).",
            className="curve-footnote",
        ),
    ]
    return html.Div(className="curve-page-body", children=parts)


@callback(
    Output("vf-st-date", "options"),
    Output("vf-st-date", "value"),
    Output("vf-st-zone", "options"),
    Output("vf-st-zone", "value"),
    Output("vf-st-segment", "options"),
    Output("vf-st-segment", "value"),
    Input("sql-warehouse-dropdown", "value"),
    Input("vf-st-refresh", "n_clicks"),
    State("vf-st-date", "value"),
    State("vf-st-zone", "value"),
    State("vf-st-segment", "value"),
    prevent_initial_call=False,
)
def _load_filters(
    warehouse_id: str | None,
    _n: int | None,
    current_date: str | None,
    current_zone: str | None,
    current_segment: str | None,
):
    zone_opts = [{"label": "All zones", "value": "ALL"}]
    seg_opts = [{"label": "All segments", "value": "ALL"}]
    if not warehouse_id:
        return [], None, zone_opts, ucp.resolve_dropdown_value(current_zone, ["ALL"]), seg_opts, ucp.resolve_dropdown_value(current_segment, ["ALL"])

    dates_sql = f"""
    SELECT DISTINCT delivery_date FROM {ucp.fq("volume_forecast_dim_intervals")}
    ORDER BY delivery_date DESC LIMIT 30
    """
    zones_sql = f"SELECT zone_code, country FROM {ucp.fq('volume_forecast_dim_zones')} ORDER BY zone_code"
    segs_sql = f"SELECT segment_code, segment_name FROM {ucp.fq('volume_forecast_dim_segments')} ORDER BY segment_code"

    d_res = ucp.run_uc_sql(warehouse_id, dates_sql)
    z_res = ucp.run_uc_sql(warehouse_id, zones_sql)
    s_res = ucp.run_uc_sql(warehouse_id, segs_sql)

    dates = [ucp.normalize_as_of(r[0]) for r in (d_res.rows if d_res.ok else []) if ucp.normalize_as_of(r[0])]
    date_opts = [{"label": d, "value": d} for d in dates]

    if z_res.ok:
        zone_opts += [{"label": f"{r[0]} — {r[1]}", "value": str(r[0])} for r in z_res.rows]
    if s_res.ok:
        seg_opts += [{"label": f"{r[0]} — {r[1]}", "value": str(r[0])} for r in s_res.rows]

    zone_values = [str(o["value"]) for o in zone_opts]
    seg_values = [str(o["value"]) for o in seg_opts]
    return (
        date_opts,
        ucp.resolve_dropdown_value(current_date, dates),
        zone_opts,
        ucp.resolve_dropdown_value(current_zone, zone_values),
        seg_opts,
        ucp.resolve_dropdown_value(current_segment, seg_values),
    )


@callback(
    Output("vf-st-body", "children"),
    Input("sql-warehouse-dropdown", "value"),
    Input("vf-st-date", "value"),
    Input("vf-st-zone", "value"),
    Input("vf-st-segment", "value"),
    Input("vf-st-refresh", "n_clicks"),
)
def _render_body(
    warehouse_id: str | None,
    delivery_date: str | None,
    zone: str | None,
    segment: str | None,
    _n: int | None,
):
    if not warehouse_id:
        return ucp.warehouse_prompt()
    if not delivery_date:
        probe = ucp.run_uc_sql(warehouse_id, f"SELECT COUNT(*) FROM {ucp.fq('volume_forecast_silver_consumption_st')}")
        if probe.ok and probe.rows and int(float(probe.rows[0][0])) > 0:
            return _alert("Delivery dates could not be loaded — choose Refresh.", kind="warn")
        return _alert("No short-term consumption data. Run `energy_trading_demo_data`, then select a connection.", kind="warn")
    return _body(
        warehouse_id,
        ucp.normalize_as_of(delivery_date) or delivery_date,
        zone or "ALL",
        segment or "ALL",
    )


@callback(
    Output("vf-st-presenter-modal", "className"),
    Input("vf-st-presenter-tip-btn", "n_clicks"),
    Input("vf-st-presenter-close", "n_clicks"),
    Input("vf-st-presenter-backdrop", "n_clicks"),
    State("vf-st-presenter-modal", "className"),
    prevent_initial_call=True,
)
def _toggle_presenter(_o, _c, _b, current: str | None):
    base = "curve-presenter-modal"
    return base if current and "curve-presenter-modal-open" in current else f"{base} curve-presenter-modal-open"
