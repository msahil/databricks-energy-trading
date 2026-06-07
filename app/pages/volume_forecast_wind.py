"""
Wind Forecasting — probabilistic wind generation for the renewables desk.
Spec: modules/volume-forecasting/specifications/05-wind-forecasting.md
"""

from __future__ import annotations

from typing import Any

import dash
from dash import Input, Output, State, callback, dcc, html
import plotly.graph_objects as go

import uc_pages as ucp
import ui_icons as uicons

_PATH = "/volume-forecasting/wind"

dash.register_page(
    __name__,
    path=_PATH,
    name="Wind Forecasting",
    title="Wind Forecasting — Volume forecasting",
)

_PAGE_TITLE = "Wind Forecasting"
_PAGE_SUMMARY = (
    "Forecast wind generation per asset at 15-minute grain by blending NWP ensembles with "
    "SCADA bias correction. Wind is the largest volume swing in the book — output is "
    "probabilistic (P10 / P50 / P90) and feeds net-volume reconciliation."
)

_KPI_LEAD = (
    "Renewables desk snapshot: fleet P50, peak generation, ensemble spread, and curtailment risk."
)
_WIDGET_FAN = (
    "Probabilistic generation fan — P10 / P50 / P90. Realised output overlays on settled intervals."
)
_WIDGET_ASSETS = (
    "Which farms drive generation at P50 — onshore baseload vs offshore peaks."
)
_WIDGET_MOVE = (
    "Forecast move when a new NWP run lands — delta since the previous vintage."
)

_PRESENTER_LEAD = ucp.PRESENTER_LEAD_CAPABILITY

_PRESENTER_SECTIONS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "1 — Pain point for traders",
        (
            "In a Northern-European book, wind is usually the largest volume swing. A few metres per second of forecast "
            "error can move hundreds of megawatts before gate close — and traders hate squaring against a single "
            "deterministic line that the latest weather run just invalidated.",
            "When a new numerical weather prediction run lands mid-morning, the prompt desk often discovers the hedge was "
            "sized on yesterday's wind profile. Open position widens, nominations slip, and imbalance cash-out follows "
            "interval by interval.",
            "Curtailment and congestion add insult to injury: even when it is physically windy, the desk may not receive "
            "the megawatts it thought it had. Risk needs a band, not a point estimate; operations needs a curtailment "
            "flag before nominating.",
        ),
    ),
    (
        "2 — Business problem this solves",
        (
            "This screen delivers probabilistic wind at asset grain — P10, P50, and P90 — by blending NWP ensembles with "
            "SCADA bias correction. The desk can size risk and decide when to re-square instead of debating a single line.",
            "Wind P50 is the largest supply leg feeding publication and official net volume. The prompt desk squares "
            "against that published number, not a draft model run in a forecaster's notebook.",
            "Forecast-move spikes and curtailment risk tie directly to what near-delivery shows as severe deviations — "
            "one governed lakehouse story from forecast through publish to gate. Say with confidence: \"We forecast the "
            "megawatts here; the prompt desk squares the residual before the gate shuts.\"",
        ),
    ),
    (
        "3 — This page and each widget",
        (
            "Page title and summary: Wind Forecasting — position this as the renewables desk live cut at fifteen-minute "
            "grain. You do not need to be a meteorologist; you need to point at P50, the fan, and curtailment risk.",
            "Page callout: Read the accent callout under the title if the audience has not seen publication yet. It "
            "anchors wind as the largest leg in net-volume reconciliation and names NWP ensembles as the driver of the "
            "uncertainty band.",
            "Toolbar: Delivery date should match near-delivery or publication for a coherent story. Zone focuses DE, NL, "
            "or portfolio. Onshore versus offshore explains different ramp shapes — offshore often peaks later and wider. "
            "Asset drill-down supports an asset-manager narrative; return to All assets for the stacked breakdown. Refresh "
            "after selecting a warehouse if the banner is empty.",
            "Status banner: Read curtailment risk first — LOW, MEDIUM, or HIGH is the desk headline flag. Read the "
            "headline like a shift note on westerlies or an offshore ramp. Finish with peak megawatts and ensemble band "
            "width — traders hear \"how big\" and \"how uncertain\" in one line.",
            "Desk KPI cards: Avg P50 is the best fleet estimate for the day — what publication will reconcile. Peak "
            "generation is where the book is most long on wind. Ensemble band width is P90 minus P10 — wide band means "
            "do not trust a single number for squaring. If curtailment is HIGH, say operations must be in the loop "
            "before nominating.",
            "Generation fan chart: Introduce the cone as weather uncertainty interval by interval, not model noise. P50 "
            "is the tradeable centre; the shaded band is what risk sizes. If actuals overlay on settled intervals, note "
            "that accuracy scores how well P50 tracked reality.",
            "Asset breakdown chart: With All assets selected, show which farms drive P50 and whether onshore baseload "
            "or offshore peaks dominate. Forecast at asset grain, roll up for zone and portfolio. The chart hides when "
            "you filter to a single farm — explain you are already at farm-level detail.",
            "Forecast move chart: \"What the latest NWP run did versus the previous vintage.\" Spikes here are why the "
            "prompt desk re-squares. Multiple forecast timestamps are governed in Delta; traders consume only the latest "
            "published cut.",
            "Close with conviction: \"Wind uncertainty is priced in bands on this page — publication turns P50 into the "
            "one megawatt number the squaring desk must respect.\"",
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
    if value is None:
        return None
    s = str(value).strip()
    if not s or s.lower() in ("none", "null", "nan"):
        return None
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


_ASSET_JOIN = f"INNER JOIN {ucp.fq('volume_forecast_dim_wind_assets')} a ON f.asset_id = a.asset_id"


def _wind_pred(zone: str, asset: str, wind_type: str, *, alias: str = "f") -> str:
    parts: list[str] = []
    if zone and zone != "ALL":
        parts.append(f"{alias}.zone_code = '{ucp.sql_escape(zone)}'")
    if asset and asset != "ALL":
        parts.append(f"{alias}.asset_id = '{ucp.sql_escape(asset)}'")
    if wind_type and wind_type != "ALL":
        parts.append(f"a.wind_type = '{ucp.sql_escape(wind_type)}'")
    return (" AND " + " AND ".join(parts)) if parts else ""


def _latest_vintage_cte(delivery_date: str, extra_pred: str, *, join_assets: bool) -> str:
    dp = ucp.sql_delivery_date_predicate("f.delivery_date", delivery_date)
    join = _ASSET_JOIN if join_assets else ""
    return f"""
    latest_vintage AS (
        SELECT MAX(f.forecast_ts) AS forecast_ts
        FROM {ucp.fq("volume_forecast_silver_wind_forecast")} f
        {join}
        WHERE {dp}{extra_pred}
    )
    """


def _fan_chart(rows: list[list[Any]]) -> go.Figure:
    fig = go.Figure()
    if not rows:
        fig.update_layout(template="plotly_white", height=360, margin=ucp.plotly_chart_margins(n_traces=3))
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
            fillcolor="rgba(16, 185, 129, 0.15)",
            line=dict(color="rgba(255,255,255,0)"),
            name="P10–P90 band",
            hoverinfo="skip",
        )
    )
    fig.add_trace(go.Scatter(x=xs, y=p50, name="P50", line=dict(color="#059669", width=2)))
    if any(v is not None for v in actual):
        fig.add_trace(
            go.Scatter(
                x=xs,
                y=[v if v is not None else None for v in actual],
                name="Actual",
                line=dict(color="#2563eb", width=2, dash="dot"),
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


def _asset_chart(rows: list[list[Any]]) -> go.Figure:
    fig = go.Figure()
    if not rows:
        fig.update_layout(template="plotly_white", height=320, margin=ucp.plotly_chart_margins(n_traces=5))
        return fig

    by_asset: dict[str, list[tuple[str, float]]] = {}
    for row in rows:
        interval, asset, p50 = str(row[0]), str(row[1]), float(row[2] or 0)
        by_asset.setdefault(asset, []).append((interval, p50))

    palette = ["#059669", "#10b981", "#34d399", "#6ee7b7", "#047857", "#065f46"]
    for i, (asset, points) in enumerate(sorted(by_asset.items())):
        points.sort(key=lambda p: p[0])
        fig.add_trace(
            go.Scatter(
                x=[p[0] for p in points],
                y=[p[1] for p in points],
                name=asset,
                stackgroup="one",
                mode="lines",
                line=dict(width=0.5, color=palette[i % len(palette)]),
                fillcolor=palette[i % len(palette)],
            )
        )
    n_traces = len(by_asset)
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
    fig.add_trace(go.Bar(x=xs, y=ys, marker_color=colors, hovertemplate="%{x}<br>Δ %{y:.2f} MW<extra></extra>"))
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
                                    html.Span("Supply leg", className="curve-page-badge"),
                                ],
                            ),
                            ucp.presenter_tip_button("vf-wind-presenter-tip-btn"),
                        ],
                    ),
                    uicons.hero_title(_PAGE_TITLE, uicons.VOLUME_FORECAST_NAV_ICONS[_PATH]),
                    html.P(_PAGE_SUMMARY, className="curve-page-summary"),
                ],
            ),
            ucp.presenter_modal(
                _PRESENTER_SECTIONS,
                modal_id="vf-wind-presenter-modal",
                close_id="vf-wind-presenter-close",
                backdrop_id="vf-wind-presenter-backdrop",
                title_id="vf-wind-presenter-modal-title",
                lead=_PRESENTER_LEAD,
            ),
            html.Div(
                className="curve-callout curve-callout-accent",
                children=html.P(
                    "Largest supply leg in net-volume reconciliation. "
                    "Ensemble spread in bronze NWP drives the P10–P90 band.",
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
                            dcc.Dropdown(id="vf-wind-date", options=[], value=None, clearable=False,
                                         className="toolbar-select st-toolbar-date", optionHeight=44),
                        ],
                    ),
                    html.Div(
                        className="curve-toolbar-field st-toolbar-field-zone",
                        children=[
                            html.Label("Zone", className="curve-toolbar-label"),
                            dcc.Dropdown(id="vf-wind-zone", options=[{"label": "All zones", "value": "ALL"}],
                                         value="ALL", clearable=False, className="toolbar-select st-toolbar-zone", optionHeight=44),
                        ],
                    ),
                    html.Div(
                        className="curve-toolbar-field st-toolbar-field-zone",
                        children=[
                            html.Label("Onshore / offshore", className="curve-toolbar-label"),
                            dcc.Dropdown(
                                id="vf-wind-type",
                                options=[
                                    {"label": "All types", "value": "ALL"},
                                    {"label": "Onshore", "value": "ONSHORE"},
                                    {"label": "Offshore", "value": "OFFSHORE"},
                                ],
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
                            html.Label("Asset", className="curve-toolbar-label"),
                            dcc.Dropdown(id="vf-wind-asset", options=[{"label": "All assets", "value": "ALL"}],
                                         value="ALL", clearable=False, className="toolbar-select st-toolbar-zone", optionHeight=44),
                        ],
                    ),
                    html.Button("Refresh", id="vf-wind-refresh", type="button", className="curve-refresh-btn"),
                ],
            ),
            dcc.Loading(id="vf-wind-loading", type="default", children=html.Div(id="vf-wind-body")),
        ],
    )


def _body(warehouse_id: str, delivery_date: str, zone: str, wind_type: str, asset: str) -> html.Div:
    dp = ucp.sql_delivery_date_predicate("delivery_date", delivery_date)
    join_assets = wind_type != "ALL"
    filt = _wind_pred(zone, asset, wind_type)
    zone_only = _wind_pred(zone, "ALL", wind_type)
    use_filtered_kpis = wind_type != "ALL" or asset != "ALL"

    if not use_filtered_kpis and zone != "ALL":
        summary_sql = f"""
        SELECT headline, total_p50_mw, peak_mw, band_width_mw, availability_pct, curtailment_risk, snapshot_ts
        FROM {ucp.fq("volume_forecast_gold_wind_summary")}
        WHERE {dp} AND zone_code = '{ucp.sql_escape(zone)}'
        LIMIT 1
        """
    elif not use_filtered_kpis:
        summary_sql = f"""
        SELECT
            MAX(headline) AS headline,
            ROUND(AVG(total_p50_mw), 1) AS total_p50_mw,
            ROUND(MAX(peak_mw), 1) AS peak_mw,
            ROUND(AVG(band_width_mw), 1) AS band_width_mw,
            ROUND(AVG(availability_pct), 1) AS availability_pct,
            MAX(CASE curtailment_risk WHEN 'HIGH' THEN 3 WHEN 'MEDIUM' THEN 2 ELSE 1 END) AS risk_rank,
            MAX(snapshot_ts) AS snapshot_ts
        FROM {ucp.fq("volume_forecast_gold_wind_summary")}
        WHERE {dp}
        """
    else:
        cte_kpi = _latest_vintage_cte(delivery_date, filt, join_assets=join_assets)
        summary_sql = f"""
        WITH {cte_kpi},
        per_interval AS (
            SELECT f.interval_start,
                   ROUND(SUM(f.p50_mw), 2) AS p50_mw,
                   ROUND(SUM(f.p10_mw), 2) AS p10_mw,
                   ROUND(SUM(f.p90_mw), 2) AS p90_mw
            FROM {ucp.fq("volume_forecast_silver_wind_forecast")} f
            {_ASSET_JOIN if join_assets else ""}
            INNER JOIN latest_vintage v ON f.forecast_ts = v.forecast_ts
            WHERE {ucp.sql_delivery_date_predicate("f.delivery_date", delivery_date)}{filt}
            GROUP BY f.interval_start
        )
        SELECT
            'Filtered wind fleet' AS headline,
            ROUND(AVG(p50_mw), 1) AS total_p50_mw,
            ROUND(MAX(p50_mw), 1) AS peak_mw,
            ROUND(AVG(p90_mw - p10_mw), 1) AS band_width_mw,
            CAST(NULL AS DOUBLE) AS availability_pct,
            1 AS risk_rank,
            CAST(NULL AS TIMESTAMP) AS snapshot_ts
        FROM per_interval
        """
    sum_res = ucp.run_uc_sql(warehouse_id, summary_sql)
    if not sum_res.ok:
        return _alert(f"Could not load wind summary: {sum_res.error}", kind="error")
    if not sum_res.rows:
        return _alert("No wind summary for this filter.", kind="warn")

    s = dict(zip(sum_res.columns, sum_res.rows[0]))
    if use_filtered_kpis:
        curtailment = "LOW"
    elif zone == "ALL":
        risk_rank = int(float(s.get("risk_rank") or 1))
        curtailment = "HIGH" if risk_rank == 3 else "MEDIUM" if risk_rank == 2 else "LOW"
    else:
        curtailment = str(s.get("curtailment_risk") or "LOW")

    total_p50 = float(s.get("total_p50_mw") or 0)
    peak_mw = float(s.get("peak_mw") or 0)
    band = float(s.get("band_width_mw") or 0)
    avail_raw = s.get("availability_pct")
    avail = float(avail_raw) if avail_raw is not None and str(avail_raw).strip() else None
    headline = str(s.get("headline") or "Wind forecast loaded")
    snapshot_ts = str(s.get("snapshot_ts") or "—")

    chart_pred = zone_only if asset == "ALL" else filt
    cte = _latest_vintage_cte(delivery_date, chart_pred, join_assets=join_assets)
    join = _ASSET_JOIN if join_assets else ""

    move_sql = f"""
    WITH {cte}
    SELECT
        ROUND(MAX(ABS(f.forecast_delta_mw)), 2) AS peak_move,
        ROUND(AVG(ABS(f.forecast_delta_mw)), 2) AS avg_move
    FROM {ucp.fq("volume_forecast_silver_wind_forecast")} f
    {join}
    INNER JOIN latest_vintage v ON f.forecast_ts = v.forecast_ts
    WHERE {ucp.sql_delivery_date_predicate("f.delivery_date", delivery_date)}{chart_pred}
      AND f.forecast_delta_mw IS NOT NULL
    """
    move_res = ucp.run_uc_sql(warehouse_id, move_sql)
    peak_move = 0.0
    avg_move = 0.0
    if move_res.ok and move_res.rows:
        m = dict(zip(move_res.columns, move_res.rows[0]))
        peak_move = float(m.get("peak_move") or 0)
        avg_move = float(m.get("avg_move") or 0)

    fan_sql = f"""
    WITH {cte}
    SELECT f.interval_start,
           ROUND(SUM(f.p10_mw), 2), ROUND(SUM(f.p50_mw), 2), ROUND(SUM(f.p90_mw), 2),
           ROUND(SUM(f.actual_mw), 2)
    FROM {ucp.fq("volume_forecast_silver_wind_forecast")} f
    {join}
    INNER JOIN latest_vintage v ON f.forecast_ts = v.forecast_ts
    WHERE {ucp.sql_delivery_date_predicate("f.delivery_date", delivery_date)}{chart_pred}
    GROUP BY f.interval_start
    ORDER BY f.interval_start
    """
    fan_res = ucp.run_uc_sql(warehouse_id, fan_sql)

    asset_sql = f"""
    WITH {cte}
    SELECT f.interval_start, f.asset_id, ROUND(SUM(f.p50_mw), 2)
    FROM {ucp.fq("volume_forecast_silver_wind_forecast")} f
    {join}
    INNER JOIN latest_vintage v ON f.forecast_ts = v.forecast_ts
    WHERE {ucp.sql_delivery_date_predicate("f.delivery_date", delivery_date)}{zone_only}
    GROUP BY f.interval_start, f.asset_id
    ORDER BY f.interval_start, f.asset_id
    """
    asset_res = ucp.run_uc_sql(warehouse_id, asset_sql)

    delta_sql = f"""
    WITH {cte}
    SELECT f.interval_start, ROUND(SUM(f.forecast_delta_mw), 2)
    FROM {ucp.fq("volume_forecast_silver_wind_forecast")} f
    {join}
    INNER JOIN latest_vintage v ON f.forecast_ts = v.forecast_ts
    WHERE {ucp.sql_delivery_date_predicate("f.delivery_date", delivery_date)}{chart_pred}
      AND f.forecast_delta_mw IS NOT NULL
    GROUP BY f.interval_start
    ORDER BY f.interval_start
    """
    delta_res = ucp.run_uc_sql(warehouse_id, delta_sql)

    banner_variant = "curve-pub-superseded" if curtailment == "HIGH" else "curve-pub-draft"
    parts: list[Any] = [
        html.Div(
            className=f"curve-publication-banner {banner_variant}",
            children=[
                html.Span(curtailment, className="curve-pub-badge"),
                html.Span(headline, className="curve-pub-headline"),
                html.Span(
                    f"Peak {peak_mw:.1f} MW · band {band:.1f} MW"
                    + (f" · availability {avail:.0f}%" if avail is not None else "")
                    + (f" · as of {snapshot_ts}" if snapshot_ts != "—" else ""),
                    className="curve-pub-meta",
                ),
            ],
        ),
        html.P(_KPI_LEAD, className="curve-section-lead"),
        html.Div(
            className="curve-outcome-row",
            children=[
                _outcome_card("Avg P50", f"{total_p50:.1f} MW"),
                _outcome_card("Peak generation", f"{peak_mw:.1f} MW"),
                _outcome_card("Ensemble band", f"{band:.1f} MW", variant="curve-outcome-warn" if band > 80 else ""),
                _outcome_card(
                    "Curtailment risk",
                    curtailment,
                    sub=f"NWP move ±{peak_move:.1f} MW",
                    variant="curve-outcome-warn" if curtailment == "HIGH" else "",
                ),
            ],
        ),
        ucp.capability_section(
            "Generation fan",
            _WIDGET_FAN,
            dcc.Graph(figure=_fan_chart(fan_res.rows if fan_res.ok else []), config={"displayModeBar": False}),
        ),
        ucp.capability_section(
            "Asset breakdown",
            _WIDGET_ASSETS,
            dcc.Graph(figure=_asset_chart(asset_res.rows if asset_res.ok else []), config={"displayModeBar": False})
            if asset == "ALL"
            else html.P(f"Asset filter set to {asset} — open All assets for the stacked breakdown.", className="curve-muted"),
        ),
        ucp.capability_section(
            "Forecast move",
            _WIDGET_MOVE,
            dcc.Graph(figure=_move_chart(delta_res.rows if delta_res.ok else []), config={"displayModeBar": False}),
        ),
        html.P(f"Snapshot for {delivery_date}; latest forecast vintage.", className="curve-footnote"),
    ]
    return html.Div(className="curve-page-body", children=parts)


@callback(
    Output("vf-wind-date", "options"), Output("vf-wind-date", "value"),
    Output("vf-wind-zone", "options"), Output("vf-wind-zone", "value"),
    Output("vf-wind-asset", "options"), Output("vf-wind-asset", "value"),
    Input("sql-warehouse-dropdown", "value"),
    Input("vf-wind-refresh", "n_clicks"),
    State("vf-wind-date", "value"),
    State("vf-wind-zone", "value"),
    State("vf-wind-asset", "value"),
    prevent_initial_call=False,
)
def _load_filters(warehouse_id, _n, current_date, current_zone, current_asset):
    zone_opts = [{"label": "All zones", "value": "ALL"}]
    asset_opts = [{"label": "All assets", "value": "ALL"}]
    if not warehouse_id:
        return [], None, zone_opts, "ALL", asset_opts, "ALL"

    d_res = ucp.run_uc_sql(warehouse_id, f"SELECT DISTINCT delivery_date FROM {ucp.fq('volume_forecast_dim_intervals')} ORDER BY delivery_date DESC LIMIT 30")
    z_res = ucp.run_uc_sql(warehouse_id, f"SELECT zone_code, country FROM {ucp.fq('volume_forecast_dim_zones')} ORDER BY zone_code")
    a_res = ucp.run_uc_sql(warehouse_id, f"SELECT asset_id, asset_name FROM {ucp.fq('volume_forecast_dim_wind_assets')} ORDER BY asset_id")

    dates = [ucp.normalize_as_of(r[0]) for r in (d_res.rows if d_res.ok else []) if ucp.normalize_as_of(r[0])]
    if z_res.ok:
        zone_opts += [{"label": f"{r[0]} — {r[1]}", "value": str(r[0])} for r in z_res.rows]
    if a_res.ok:
        asset_opts += [{"label": f"{r[0]} — {r[1]}", "value": str(r[0])} for r in a_res.rows]

    return (
        [{"label": d, "value": d} for d in dates],
        ucp.resolve_dropdown_value(current_date, dates),
        zone_opts,
        ucp.resolve_dropdown_value(current_zone, [o["value"] for o in zone_opts]),
        asset_opts,
        ucp.resolve_dropdown_value(current_asset, [o["value"] for o in asset_opts]),
    )


@callback(
    Output("vf-wind-body", "children"),
    Input("sql-warehouse-dropdown", "value"),
    Input("vf-wind-date", "value"),
    Input("vf-wind-zone", "value"),
    Input("vf-wind-type", "value"),
    Input("vf-wind-asset", "value"),
    Input("vf-wind-refresh", "n_clicks"),
)
def _render_body(warehouse_id, delivery_date, zone, wind_type, asset, _n):
    if not warehouse_id:
        return ucp.warehouse_prompt()
    if not delivery_date:
        probe = ucp.run_uc_sql(warehouse_id, f"SELECT COUNT(*) FROM {ucp.fq('volume_forecast_silver_wind_forecast')}")
        if probe.ok and probe.rows and int(float(probe.rows[0][0])) > 0:
            return _alert("Delivery dates could not be loaded — choose Refresh.", kind="warn")
        return _alert("No wind data. Run `energy_trading_demo_data`, then select a connection.", kind="warn")
    return _body(warehouse_id, ucp.normalize_as_of(delivery_date) or delivery_date, zone or "ALL", wind_type or "ALL", asset or "ALL")


@callback(
    Output("vf-wind-presenter-modal", "className"),
    Input("vf-wind-presenter-tip-btn", "n_clicks"),
    Input("vf-wind-presenter-close", "n_clicks"),
    Input("vf-wind-presenter-backdrop", "n_clicks"),
    State("vf-wind-presenter-modal", "className"),
    prevent_initial_call=True,
)
def _toggle_presenter(_o, _c, _b, current):
    base = "curve-presenter-modal"
    return base if current and "curve-presenter-modal-open" in current else f"{base} curve-presenter-modal-open"
