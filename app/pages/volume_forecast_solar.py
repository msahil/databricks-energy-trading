"""
Solar Forecasting — probabilistic PV generation for the renewables desk.
Spec: modules/volume-forecasting/specifications/06-solar-forecasting.md
"""

from __future__ import annotations

from typing import Any

import dash
from dash import Input, Output, State, callback, dcc, html
import plotly.graph_objects as go

import uc_pages as ucp
import ui_icons as uicons

_PATH = "/volume-forecasting/solar"

dash.register_page(
    __name__,
    path=_PATH,
    name="Solar Forecasting",
    title="Solar Forecasting — Volume forecasting",
)

_PAGE_TITLE = "Solar Forecasting"
_PAGE_SUMMARY = (
    "Forecast utility-scale PV from irradiance, cloud cover, and satellite nowcasts, reconciled with "
    "behind-the-meter PV already netted out of consumption so rooftop kW is never double-counted. "
    "Drives the midday surplus and negative-price risk the prompt desk lives with."
)

_KPI_LEAD = (
    "Renewables desk snapshot: fleet P50, midday peak, cloud-driven band, and BTM PV already netted in demand."
)
_WIDGET_FAN = (
    "Probabilistic generation fan — P10 / P50 / P90 with clear-sky theoretical output. "
    "Realised SCADA overlays on settled intervals."
)
_WIDGET_ASSETS = (
    "Which farms drive midday surplus at P50 — tracking type and zone contribution."
)
_WIDGET_BTM = (
    "Utility-scale supply vs behind-the-meter PV netted in Smart Metering (04). "
    "Only utility-scale counts toward published supply — BTM is already in demand."
)

_PRESENTER_LEAD = ucp.PRESENTER_LEAD_CAPABILITY

_PRESENTER_SECTIONS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "1 — Pain point for traders",
        (
            "Solar builds the midday volume surplus that drives negative prices and cannibalization in European "
            "markets. Cloud cover can erase hundreds of megawatts in an hour — often after traders already sold the "
            "sunny shape into intraday.",
            "Confusing rooftop PV with utility-scale farms double-counts supply and breaks net volume reconciliation. "
            "Experienced desks treat that as a basic hygiene failure, not a minor modelling detail.",
            "Traders need clear-sky versus expected irradiance and a probabilistic band — not a single megawatt line "
            "that the latest satellite loop just invalidated.",
        ),
    ),
    (
        "2 — Business problem this solves",
        (
            "This page forecasts probabilistic utility-scale solar at asset grain for the supply leg of publication. "
            "Behind-the-meter rooftop PV stays in the demand leg via Smart Metering — reconciliation rules prevent "
            "double-count.",
            "Negative-price risk flags connect directly to prompt squaring and balancing behaviour — the same commercial "
            "story as wind curtailment on the renewables desk. The BTM reconciliation panel proves governance: supply "
            "counts only what the grid sees at utility scale.",
            "Say with confidence: \"The midday surplus you see here is why intraday price collapsed — publication carries "
            "that leg as the official supply number.\"",
        ),
    ),
    (
        "3 — This page and each widget",
        (
            "Page title and summary: Solar Forecasting — irradiance-driven probabilistic generation at fifteen-minute "
            "grain. Emphasise utility-scale for supply; BTM netted in demand.",
            "Toolbar: Delivery date, zone, and asset filters — keep the date aligned with wind and publication. Drill "
            "to one farm for an asset story; use All assets for portfolio midday surplus.",
            "Status banner: Lead with negative-price risk level, then read the headline like a shift note on cloud "
            "cover or clear-sky conditions. Midday peak megawatts and band width complete the scan.",
            "Desk KPI cards: Day total P50, midday peak interval, clear-sky delta, and negative-price risk — answer "
            "\"how sunny,\" \"how peaky,\" and \"how dangerous for capture price\" in one row.",
            "Generation fan chart: P10, P50, and P90 with clear-sky reference. The gap below clear-sky shows cloud "
            "impact traders feel in real time. P50 is what publication reconciles for utility-scale supply.",
            "Asset breakdown chart: Which farms drive the midday surplus — utility-scale only. Tie to zonal "
            "cannibalization if the room trades capture price.",
            "BTM reconciliation panel: Show rooftop PV excluded from supply because it is already netted in consumption. "
            "This is the answer when someone asks how you avoid double-counting solar.",
            "Close with conviction: \"Solar moves faster than wind intraday — banded forecast here, official P50 in "
            "publication, euros of error in accuracy if we get it wrong.\"",
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


def _solar_pred(zone: str, asset: str, *, alias: str = "f") -> str:
    parts: list[str] = []
    if zone and zone != "ALL":
        parts.append(f"{alias}.zone_code = '{ucp.sql_escape(zone)}'")
    if asset and asset != "ALL":
        parts.append(f"{alias}.asset_id = '{ucp.sql_escape(asset)}'")
    return (" AND " + " AND ".join(parts)) if parts else ""


def _btm_pred(zone: str) -> str:
    if zone and zone != "ALL":
        return f" AND zone_code = '{ucp.sql_escape(zone)}'"
    return ""


def _latest_vintage_cte(delivery_date: str, extra_pred: str) -> str:
    dp = ucp.sql_delivery_date_predicate("f.delivery_date", delivery_date)
    return f"""
    latest_vintage AS (
        SELECT MAX(f.forecast_ts) AS forecast_ts
        FROM {ucp.fq("volume_forecast_silver_solar_forecast")} f
        WHERE {dp}{extra_pred}
    )
    """


def _fan_chart(rows: list[list[Any]]) -> go.Figure:
    fig = go.Figure()
    if not rows:
        fig.update_layout(template="plotly_white", height=360, margin=ucp.plotly_chart_margins(n_traces=4))
        return fig

    xs, p10, p50, p90, clear_sky, actual = [], [], [], [], [], []
    for row in rows:
        xs.append(str(row[0]))
        p10.append(float(row[1] or 0))
        p50.append(float(row[2] or 0))
        p90.append(float(row[3] or 0))
        clear_sky.append(float(row[4] or 0))
        actual.append(_opt_float(row[5]))

    fig.add_trace(
        go.Scatter(
            x=xs + xs[::-1],
            y=p90 + p10[::-1],
            fill="toself",
            fillcolor="rgba(245, 158, 11, 0.15)",
            line=dict(color="rgba(255,255,255,0)"),
            name="P10–P90 band",
            hoverinfo="skip",
        )
    )
    fig.add_trace(go.Scatter(x=xs, y=p50, name="P50", line=dict(color="#d97706", width=2)))
    fig.add_trace(
        go.Scatter(
            x=xs,
            y=clear_sky,
            name="Clear sky",
            line=dict(color="#fbbf24", width=1.5, dash="dash"),
            mode="lines",
        )
    )
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
    n_traces = 4 if any(v is not None for v in actual) else 3
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

    palette = ["#d97706", "#f59e0b", "#fbbf24", "#fcd34d", "#b45309", "#92400e"]
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


def _btm_chart(rows: list[list[Any]]) -> go.Figure:
    """Utility-scale P50 vs BTM PV netted in demand."""
    fig = go.Figure()
    if not rows:
        fig.update_layout(template="plotly_white", height=280, margin=ucp.plotly_chart_margins(n_traces=2))
        return fig

    xs, utility, btm = [], [], []
    for row in rows:
        xs.append(str(row[0]))
        utility.append(float(row[1] or 0))
        btm.append(float(row[2] or 0))

    fig.add_trace(
        go.Scatter(
            x=xs,
            y=utility,
            name="Utility-scale P50",
            line=dict(color="#d97706", width=2),
            mode="lines",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=xs,
            y=btm,
            name="BTM PV (netted in 04)",
            line=dict(color="#6366f1", width=2, dash="dash"),
            mode="lines",
        )
    )
    fig.update_layout(
        yaxis_title="MW",
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
                                    html.Span("Supply leg", className="curve-page-badge"),
                                ],
                            ),
                            ucp.presenter_tip_button("vf-solar-presenter-tip-btn"),
                        ],
                    ),
                    uicons.hero_title(_PAGE_TITLE, uicons.VOLUME_FORECAST_NAV_ICONS[_PATH]),
                    html.P(_PAGE_SUMMARY, className="curve-page-summary"),
                ],
            ),
            ucp.presenter_modal(
                _PRESENTER_SECTIONS,
                modal_id="vf-solar-presenter-modal",
                close_id="vf-solar-presenter-close",
                backdrop_id="vf-solar-presenter-backdrop",
                title_id="vf-solar-presenter-modal-title",
                lead=_PRESENTER_LEAD,
            ),
            html.Div(
                className="curve-callout curve-callout-accent",
                children=html.P(
                    "Second supply leg in net-volume reconciliation. BTM rooftop PV is netted in Smart Metering (04) — "
                    "only utility-scale farms count here.",
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
                                id="vf-solar-date",
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
                                id="vf-solar-zone",
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
                            html.Label("Asset", className="curve-toolbar-label"),
                            dcc.Dropdown(
                                id="vf-solar-asset",
                                options=[{"label": "All assets", "value": "ALL"}],
                                value="ALL",
                                clearable=False,
                                className="toolbar-select st-toolbar-zone",
                                optionHeight=44,
                            ),
                        ],
                    ),
                    html.Button("Refresh", id="vf-solar-refresh", type="button", className="curve-refresh-btn"),
                ],
            ),
            dcc.Loading(id="vf-solar-loading", type="default", children=html.Div(id="vf-solar-body")),
        ],
    )


def _body(warehouse_id: str, delivery_date: str, zone: str, asset: str) -> html.Div:
    dp = ucp.sql_delivery_date_predicate("delivery_date", delivery_date)
    filt = _solar_pred(zone, asset)
    zone_only = _solar_pred(zone, "ALL")
    use_filtered_kpis = asset != "ALL"

    if not use_filtered_kpis and zone != "ALL":
        summary_sql = f"""
        SELECT headline, total_p50_mw, midday_peak_mw, band_width_mw, btm_pv_mw,
               negative_price_risk, snapshot_ts
        FROM {ucp.fq("volume_forecast_gold_solar_summary")}
        WHERE {dp} AND zone_code = '{ucp.sql_escape(zone)}'
        LIMIT 1
        """
    elif not use_filtered_kpis:
        summary_sql = f"""
        SELECT
            MAX(headline) AS headline,
            ROUND(AVG(total_p50_mw), 1) AS total_p50_mw,
            ROUND(MAX(midday_peak_mw), 1) AS midday_peak_mw,
            ROUND(AVG(band_width_mw), 1) AS band_width_mw,
            ROUND(SUM(btm_pv_mw), 1) AS btm_pv_mw,
            MAX(CASE negative_price_risk WHEN 'HIGH' THEN 3 WHEN 'MEDIUM' THEN 2 ELSE 1 END) AS risk_rank,
            MAX(snapshot_ts) AS snapshot_ts
        FROM {ucp.fq("volume_forecast_gold_solar_summary")}
        WHERE {dp}
        """
    else:
        cte_kpi = _latest_vintage_cte(delivery_date, filt)
        summary_sql = f"""
        WITH {cte_kpi},
        per_interval AS (
            SELECT f.interval_start,
                   ROUND(SUM(f.p50_mw), 2) AS p50_mw,
                   ROUND(SUM(f.p10_mw), 2) AS p10_mw,
                   ROUND(SUM(f.p90_mw), 2) AS p90_mw
            FROM {ucp.fq("volume_forecast_silver_solar_forecast")} f
            INNER JOIN latest_vintage v ON f.forecast_ts = v.forecast_ts
            WHERE {ucp.sql_delivery_date_predicate("f.delivery_date", delivery_date)}{filt}
            GROUP BY f.interval_start
        )
        SELECT
            'Filtered solar fleet' AS headline,
            ROUND(AVG(p50_mw), 1) AS total_p50_mw,
            ROUND(MAX(p50_mw), 1) AS midday_peak_mw,
            ROUND(AVG(p90_mw - p10_mw), 1) AS band_width_mw,
            CAST(NULL AS DOUBLE) AS btm_pv_mw,
            1 AS risk_rank,
            CAST(NULL AS TIMESTAMP) AS snapshot_ts
        FROM per_interval
        """
    sum_res = ucp.run_uc_sql(warehouse_id, summary_sql)
    if not sum_res.ok:
        return _alert(f"Could not load solar summary: {sum_res.error}", kind="error")
    if not sum_res.rows:
        return _alert("No solar summary for this filter.", kind="warn")

    s = dict(zip(sum_res.columns, sum_res.rows[0]))
    if use_filtered_kpis:
        neg_risk = "LOW"
    elif zone == "ALL":
        risk_rank = int(float(s.get("risk_rank") or 1))
        neg_risk = "HIGH" if risk_rank == 3 else "MEDIUM" if risk_rank == 2 else "LOW"
    else:
        neg_risk = str(s.get("negative_price_risk") or "LOW")

    total_p50 = float(s.get("total_p50_mw") or 0)
    midday_peak = float(s.get("midday_peak_mw") or 0)
    band = float(s.get("band_width_mw") or 0)
    btm_raw = s.get("btm_pv_mw")
    btm_pv = float(btm_raw) if btm_raw is not None and str(btm_raw).strip() else None
    headline = str(s.get("headline") or "Solar forecast loaded")
    snapshot_ts = str(s.get("snapshot_ts") or "—")

    chart_pred = zone_only if asset == "ALL" else filt
    cte = _latest_vintage_cte(delivery_date, chart_pred)

    fan_sql = f"""
    WITH {cte}
    SELECT f.interval_start,
           ROUND(SUM(f.p10_mw), 2), ROUND(SUM(f.p50_mw), 2), ROUND(SUM(f.p90_mw), 2),
           ROUND(SUM(f.clear_sky_mw), 2), ROUND(SUM(f.actual_mw), 2)
    FROM {ucp.fq("volume_forecast_silver_solar_forecast")} f
    INNER JOIN latest_vintage v ON f.forecast_ts = v.forecast_ts
    WHERE {ucp.sql_delivery_date_predicate("f.delivery_date", delivery_date)}{chart_pred}
    GROUP BY f.interval_start
    ORDER BY f.interval_start
    """
    fan_res = ucp.run_uc_sql(warehouse_id, fan_sql)

    asset_sql = f"""
    WITH {cte}
    SELECT f.interval_start, f.asset_id, ROUND(SUM(f.p50_mw), 2)
    FROM {ucp.fq("volume_forecast_silver_solar_forecast")} f
    INNER JOIN latest_vintage v ON f.forecast_ts = v.forecast_ts
    WHERE {ucp.sql_delivery_date_predicate("f.delivery_date", delivery_date)}{zone_only}
    GROUP BY f.interval_start, f.asset_id
    ORDER BY f.interval_start, f.asset_id
    """
    asset_res = ucp.run_uc_sql(warehouse_id, asset_sql)

    btm_sql = f"""
    WITH {cte},
    utility AS (
        SELECT f.interval_start, ROUND(SUM(f.p50_mw), 2) AS utility_mw
        FROM {ucp.fq("volume_forecast_silver_solar_forecast")} f
        INNER JOIN latest_vintage v ON f.forecast_ts = v.forecast_ts
        WHERE {ucp.sql_delivery_date_predicate("f.delivery_date", delivery_date)}{zone_only}
        GROUP BY f.interval_start
    ),
    btm AS (
        SELECT interval_start, ROUND(SUM(btm_pv_mw), 2) AS btm_mw
        FROM {ucp.fq("volume_forecast_silver_btm_pv")}
        WHERE {ucp.sql_delivery_date_predicate("delivery_date", delivery_date)}{_btm_pred(zone)}
        GROUP BY interval_start
    )
    SELECT u.interval_start, u.utility_mw, COALESCE(b.btm_mw, 0)
    FROM utility u
    LEFT JOIN btm b ON u.interval_start = b.interval_start
    ORDER BY u.interval_start
    """
    btm_res = ucp.run_uc_sql(warehouse_id, btm_sql)

    banner_variant = "curve-pub-superseded" if neg_risk == "HIGH" else "curve-pub-draft"
    parts: list[Any] = [
        html.Div(
            className=f"curve-publication-banner {banner_variant}",
            children=[
                html.Span(neg_risk, className="curve-pub-badge"),
                html.Span(headline, className="curve-pub-headline"),
                html.Span(
                    f"Midday peak {midday_peak:.1f} MW · band {band:.1f} MW"
                    + (f" · BTM netted {btm_pv:.1f} MW avg" if btm_pv is not None else "")
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
                _outcome_card(
                    "Midday peak",
                    f"{midday_peak:.1f} MW",
                    variant="curve-outcome-warn" if midday_peak > 200 else "",
                ),
                _outcome_card("Cloud band", f"{band:.1f} MW", variant="curve-outcome-warn" if band > 50 else ""),
                _outcome_card(
                    "BTM PV netted",
                    f"{btm_pv:.1f} MW" if btm_pv is not None else "—",
                    sub="already in demand (04)",
                    variant="",
                ),
            ],
        ),
        ucp.capability_section(
            "Generation fan",
            _WIDGET_FAN,
            dcc.Graph(
                figure=_fan_chart(fan_res.rows if fan_res.ok else []),
                config={"displayModeBar": False},
            ),
        ),
        ucp.capability_section(
            "Asset breakdown",
            _WIDGET_ASSETS,
            dcc.Graph(
                figure=_asset_chart(asset_res.rows if asset_res.ok else []),
                config={"displayModeBar": False},
            )
            if asset == "ALL"
            else html.P(
                f"Asset filter set to {asset} — open All assets for the stacked breakdown.",
                className="curve-muted",
            ),
        ),
        ucp.capability_section(
            "BTM reconciliation",
            _WIDGET_BTM,
            dcc.Graph(
                figure=_btm_chart(btm_res.rows if btm_res.ok else []),
                config={"displayModeBar": False},
            )
            if asset == "ALL"
            else html.P(
                "BTM reconciliation is zone-level — open All assets to compare utility-scale vs rooftop PV.",
                className="curve-muted",
            ),
        ),
        html.P(f"Snapshot for {delivery_date}; latest forecast vintage.", className="curve-footnote"),
    ]
    return html.Div(className="curve-page-body", children=parts)


@callback(
    Output("vf-solar-date", "options"),
    Output("vf-solar-date", "value"),
    Output("vf-solar-zone", "options"),
    Output("vf-solar-zone", "value"),
    Output("vf-solar-asset", "options"),
    Output("vf-solar-asset", "value"),
    Input("sql-warehouse-dropdown", "value"),
    Input("vf-solar-refresh", "n_clicks"),
    State("vf-solar-date", "value"),
    State("vf-solar-zone", "value"),
    State("vf-solar-asset", "value"),
    prevent_initial_call=False,
)
def _load_filters(warehouse_id, _n, current_date, current_zone, current_asset):
    zone_opts = [{"label": "All zones", "value": "ALL"}]
    asset_opts = [{"label": "All assets", "value": "ALL"}]
    if not warehouse_id:
        return [], None, zone_opts, "ALL", asset_opts, "ALL"

    d_res = ucp.run_uc_sql(
        warehouse_id,
        f"SELECT DISTINCT delivery_date FROM {ucp.fq('volume_forecast_dim_intervals')} ORDER BY delivery_date DESC LIMIT 30",
    )
    z_res = ucp.run_uc_sql(
        warehouse_id,
        f"SELECT zone_code, country FROM {ucp.fq('volume_forecast_dim_zones')} ORDER BY zone_code",
    )
    a_res = ucp.run_uc_sql(
        warehouse_id,
        f"SELECT asset_id, asset_name FROM {ucp.fq('volume_forecast_dim_solar_assets')} ORDER BY asset_id",
    )

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
    Output("vf-solar-body", "children"),
    Input("sql-warehouse-dropdown", "value"),
    Input("vf-solar-date", "value"),
    Input("vf-solar-zone", "value"),
    Input("vf-solar-asset", "value"),
    Input("vf-solar-refresh", "n_clicks"),
)
def _render_body(warehouse_id, delivery_date, zone, asset, _n):
    if not warehouse_id:
        return ucp.warehouse_prompt()
    if not delivery_date:
        probe = ucp.run_uc_sql(warehouse_id, f"SELECT COUNT(*) FROM {ucp.fq('volume_forecast_silver_solar_forecast')}")
        if probe.ok and probe.rows and int(float(probe.rows[0][0])) > 0:
            return _alert("Delivery dates could not be loaded — choose Refresh.", kind="warn")
        return _alert("No solar data. Run `energy_trading_demo_data`, then select a connection.", kind="warn")
    return _body(warehouse_id, ucp.normalize_as_of(delivery_date) or delivery_date, zone or "ALL", asset or "ALL")


@callback(
    Output("vf-solar-presenter-modal", "className"),
    Input("vf-solar-presenter-tip-btn", "n_clicks"),
    Input("vf-solar-presenter-close", "n_clicks"),
    Input("vf-solar-presenter-backdrop", "n_clicks"),
    State("vf-solar-presenter-modal", "className"),
    prevent_initial_call=True,
)
def _toggle_presenter(_o, _c, _b, current):
    base = "curve-presenter-modal"
    return base if current and "curve-presenter-modal-open" in current else f"{base} curve-presenter-modal-open"
