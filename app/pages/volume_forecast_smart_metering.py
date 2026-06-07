"""
Smart Metering — volume forecasting data backbone.
Spec: modules/volume-forecasting/specifications/04-smart-metering.md
"""

from __future__ import annotations

from typing import Any

import dash
from dash import Input, Output, State, callback, dcc, html
import plotly.graph_objects as go

import uc_pages as ucp
import ui_icons as uicons

_PATH = "/volume-forecasting/smart-metering"

dash.register_page(
    __name__,
    path=_PATH,
    name="Smart Metering",
    title="Smart Metering — Volume forecasting",
)

_PAGE_TITLE = "Smart Metering"
_PAGE_SUMMARY = (
    "Turn millions of AMI interval reads into one governed, privacy-safe net load profile. "
    "Metering operations see feed completeness and quality gates; forecasting analysts see "
    "segment-level net load after behind-the-meter PV is deducted — the shared input every "
    "consumption forecast reads."
)

_KPI_LEAD = (
    "At-a-glance metering health for the selected day: how complete the feed is, how much "
    "rooftop PV was deducted, and whether the curated profile passed the quality gate."
)
_WIDGET_NET_LOAD = (
    "Net load by segment across the day — gross consumption minus behind-the-meter PV. "
    "This is the profile short-term and long-term consumption forecasts anchor on."
)
_WIDGET_BTM = (
    "Behind-the-meter PV generation deducted from gross load. Without this strip, "
    "residential segments would look like pure consumption when the sun is out."
)
_WIDGET_QUALITY = (
    "Per zone and segment: completeness, lateness, and corrupt-read rates. "
    "A BREACH here blocks trust in every downstream forecast."
)

_PRESENTER_LEAD = ucp.PRESENTER_LEAD_CAPABILITY

_PRESENTER_SECTIONS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "1 — Pain point for traders",
        (
            "Every consumption forecast is only as good as the meter profile underneath it — but advanced metering "
            "infrastructure feeds arrive late, gap, duplicate, and corrupt across millions of endpoints. Problems surface "
            "in nominations and imbalance, not in the metering team's inbox.",
            "Behind-the-meter rooftop PV the grid never sees inflates gross demand if you forget to deduct it. Traders "
            "then double-count solar when utility-scale supply is added on the renewables pages — an error experienced "
            "desks catch immediately.",
            "Forecasters cannot defend a load shape traders do not trust. When evening peak on the chart does not match "
            "what schedulers see in reality, the whole short-term and publication chain loses credibility.",
        ),
    ),
    (
        "2 — Business problem this solves",
        (
            "Smart Metering validates reads, deducts behind-the-meter PV, and rolls meters into privacy-safe net-load "
            "shapes above a k-anonymity threshold. Fix the profile here before you trust short-term or long-term "
            "consumption forecasts.",
            "The quality gate — GOOD versus BREACH — blocks bad data from propagating into publication and imbalance "
            "cash-out. Unity Catalog governs access; aggregates protect household privacy while the desk gets trusted shapes.",
            "When you need a blunt line that lands: \"Garbage meters in, garbage nominations out — this capability is "
            "where we stop that.\"",
        ),
    ),
    (
        "3 — This page and each widget",
        (
            "Page title and summary: Smart Metering — the foundation layer for all downstream demand forecasting. "
            "Position it early in the volume-forecasting walk if the audience questions data trust.",
            "Toolbar: Profile version, zone, and segment filters. Profile version matters for audit — say when this "
            "curated shape was produced.",
            "Status banner: Feed completeness percentage, quality gate status, and profile as-of timestamp. If the "
            "gate shows BREACH, stop and say downstream forecasts should not be trusted until metering ops clears the "
            "feed — traders respect that honesty.",
            "Desk KPI cards: Meters in profile, completeness, behind-the-meter PV deducted in megawatts, segments "
            "covered — headline health metrics for metering operations and forecasting alike.",
            "Net load profile chart: Segment shapes after BTM deduction — residential evening peak versus industrial "
            "flatness. This is the shape short-term weather models amplify.",
            "BTM PV deduction chart: Show rooftop generation removed from gross demand. Explain this prevents "
            "double-counting with utility-scale solar on the supply leg — a reconciliation rule publication enforces.",
            "Data quality panel: Late reads, gaps, outliers, and SLA breach flags — where metering operations lives. "
            "Link a breach here to risk on publication if someone asks about end-to-end governance.",
            "Close with conviction: \"Short-term and long-term consumption both inherit this profile — one governed "
            "foundation for the entire demand leg of net volume.\"",
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


def _net_load_chart(rows: list[list[Any]]) -> go.Figure:
    """Stacked area: net_load_mw by segment over interval_start."""
    fig = go.Figure()
    if not rows:
        fig.update_layout(template="plotly_white", height=340, margin=ucp.plotly_chart_margins())
        return fig

    by_segment: dict[str, list[tuple[str, float]]] = {}
    for row in rows:
        interval, segment, net = str(row[0]), str(row[1]), float(row[2] or 0)
        by_segment.setdefault(segment, []).append((interval, net))

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
        height=340,
        margin=ucp.plotly_chart_margins(n_traces=n_traces),
        xaxis_tickangle=-45,
        legend=ucp.plotly_legend(n_traces=n_traces),
    )
    return fig


def _btm_chart(profile_rows: list[list[Any]], btm_rows: list[list[Any]]) -> go.Figure:
    """Gross load, net load, and BTM PV on one chart."""
    fig = go.Figure()
    if not profile_rows and not btm_rows:
        fig.update_layout(template="plotly_white", height=280, margin=ucp.plotly_chart_margins(n_traces=3))
        return fig

    gross: dict[str, float] = {}
    net: dict[str, float] = {}
    for row in profile_rows:
        interval = str(row[0])
        gross[interval] = gross.get(interval, 0.0) + float(row[1] or 0)
        net[interval] = net.get(interval, 0.0) + float(row[2] or 0)

    btm: dict[str, float] = {}
    for row in btm_rows:
        interval = str(row[0])
        btm[interval] = btm.get(interval, 0.0) + float(row[1] or 0)

    xs = sorted(set(gross) | set(btm))
    if xs:
        fig.add_trace(go.Scatter(x=xs, y=[gross.get(x, 0) for x in xs], name="Gross load", line=dict(color="#94a3b8")))
        fig.add_trace(go.Scatter(x=xs, y=[net.get(x, 0) for x in xs], name="Net load", line=dict(color="#2563eb")))
        fig.add_trace(
            go.Scatter(
                x=xs,
                y=[btm.get(x, 0) for x in xs],
                name="BTM PV deducted",
                fill="tozeroy",
                line=dict(color="#f59e0b"),
            )
        )
    n_traces = 3
    fig.update_layout(
        yaxis_title="MW",
        template="plotly_white",
        height=280,
        margin=ucp.plotly_chart_margins(n_traces=n_traces),
        xaxis_tickangle=-45,
        legend=ucp.plotly_legend(n_traces=n_traces),
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
                                    html.Span("Data backbone", className="curve-page-badge"),
                                ],
                            ),
                            ucp.presenter_tip_button("vf-sm-presenter-tip-btn"),
                        ],
                    ),
                    uicons.hero_title(_PAGE_TITLE, uicons.VOLUME_FORECAST_NAV_ICONS[_PATH]),
                    html.P(_PAGE_SUMMARY, className="curve-page-summary"),
                ],
            ),
            ucp.presenter_modal(
                _PRESENTER_SECTIONS,
                modal_id="vf-sm-presenter-modal",
                close_id="vf-sm-presenter-close",
                backdrop_id="vf-sm-presenter-backdrop",
                title_id="vf-sm-presenter-modal-title",
                lead=_PRESENTER_LEAD,
            ),
            html.Div(
                className="curve-callout curve-callout-accent",
                children=html.P(
                    "Aggregated above k-anonymity — individual meters are never exposed. "
                    "Every consumption forecast reads this curated profile.",
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
                                id="vf-sm-date",
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
                                id="vf-sm-zone",
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
                                id="vf-sm-segment",
                                options=[{"label": "All segments", "value": "ALL"}],
                                value="ALL",
                                clearable=False,
                                className="toolbar-select st-toolbar-zone",
                                optionHeight=44,
                            ),
                        ],
                    ),
                    html.Button("Refresh", id="vf-sm-refresh", type="button", className="curve-refresh-btn"),
                ],
            ),
            dcc.Loading(id="vf-sm-loading", type="default", children=html.Div(id="vf-sm-body")),
        ],
    )


def _zone_segment_pred(zone: str, segment: str) -> str:
    parts: list[str] = []
    if zone and zone != "ALL":
        parts.append(f"zone_code = '{ucp.sql_escape(zone)}'")
    if segment and segment != "ALL":
        parts.append(f"segment_code = '{ucp.sql_escape(segment)}'")
    return (" AND " + " AND ".join(parts)) if parts else ""


def _body(warehouse_id: str, delivery_date: str, zone: str, segment: str) -> html.Div:
    dp = ucp.sql_delivery_date_predicate("delivery_date", delivery_date)
    filt = _zone_segment_pred(zone, segment)

    quality_sql = f"""
    SELECT
        ROUND(AVG(completeness_pct), 1) AS completeness_pct,
        ROUND(AVG(late_read_pct), 1) AS late_read_pct,
        ROUND(AVG(corrupt_read_pct), 1) AS corrupt_read_pct,
        SUM(imputed_intervals) AS imputed_intervals,
        MAX(CASE dq_status WHEN 'BREACH' THEN 3 WHEN 'WATCH' THEN 2 WHEN 'GOOD' THEN 1 ELSE 0 END) AS dq_rank,
        COUNT(*) AS n_rows
    FROM {ucp.fq("volume_forecast_gold_metering_quality")}
    WHERE {dp}{filt}
    """
    q_res = ucp.run_uc_sql(warehouse_id, quality_sql)
    if not q_res.ok:
        return _alert(f"Could not load metering quality: {q_res.error}", kind="error")
    if not q_res.rows or int(float(q_res.rows[0][5] or 0)) == 0:
        return _alert("No metering quality data for this filter. Try another date or zone.", kind="warn")

    q = dict(zip(q_res.columns, q_res.rows[0]))
    dq_rank = int(float(q.get("dq_rank") or 0))
    dq_status = "BREACH" if dq_rank == 3 else "WATCH" if dq_rank == 2 else "GOOD"
    completeness = float(q.get("completeness_pct") or 0)
    corrupt = float(q.get("corrupt_read_pct") or 0)
    late = float(q.get("late_read_pct") or 0)
    imputed = int(float(q.get("imputed_intervals") or 0))

    profile_meta_sql = f"""
    SELECT MAX(profile_version) AS profile_version, MAX(as_of_ts) AS as_of_ts
    FROM {ucp.fq("volume_forecast_silver_meter_profile")}
    WHERE {dp}{filt}
    """
    meta_res = ucp.run_uc_sql(warehouse_id, profile_meta_sql)
    profile_version = "—"
    as_of_ts = "—"
    if meta_res.ok and meta_res.rows:
        m = dict(zip(meta_res.columns, meta_res.rows[0]))
        profile_version = str(m.get("profile_version") or "—")
        as_of_ts = str(m.get("as_of_ts") or "—")

    btm_sql = f"""
    SELECT ROUND(SUM(btm_pv_mw) * 0.25, 1) AS btm_mwh
    FROM {ucp.fq("volume_forecast_silver_btm_pv")}
    WHERE {dp}{filt}
    """
    btm_res = ucp.run_uc_sql(warehouse_id, btm_sql)
    btm_mwh = float(btm_res.rows[0][0] or 0) if btm_res.ok and btm_res.rows else 0.0

    profile_sql = f"""
    SELECT interval_start, segment_code, gross_load_mw, net_load_mw
    FROM {ucp.fq("volume_forecast_silver_meter_profile")}
    WHERE {dp}{filt}
    ORDER BY interval_start, segment_code
    """
    prof_res = ucp.run_uc_sql(warehouse_id, profile_sql)

    btm_ts_sql = f"""
    SELECT interval_start, SUM(btm_pv_mw) AS btm_pv_mw
    FROM {ucp.fq("volume_forecast_silver_btm_pv")}
    WHERE {dp}{filt}
    GROUP BY interval_start
    ORDER BY interval_start
    """
    btm_ts_res = ucp.run_uc_sql(warehouse_id, btm_ts_sql)

    grid_sql = f"""
    SELECT zone_code, segment_code,
           ROUND(completeness_pct, 1), ROUND(late_read_pct, 1),
           ROUND(corrupt_read_pct, 1), imputed_intervals, dq_status
    FROM {ucp.fq("volume_forecast_gold_metering_quality")}
    WHERE {dp}{filt}
    ORDER BY zone_code, segment_code
    """
    grid_res = ucp.run_uc_sql(warehouse_id, grid_sql)

    banner_variant = "curve-pub-draft" if dq_status == "GOOD" else "curve-pub-superseded"
    headline = (
        "Feed within SLA — profile ready for downstream forecasts"
        if dq_status == "GOOD"
        else "Quality watch — review imputed intervals before trusting forecasts"
        if dq_status == "WATCH"
        else "Quality breach — do not publish forecasts from this profile"
    )

    parts: list[Any] = [
        html.Div(
            className=f"curve-publication-banner {banner_variant}",
            children=[
                html.Span(dq_status, className="curve-pub-badge"),
                html.Span(headline, className="curve-pub-headline"),
                html.Span(
                    f"Completeness {completeness:.1f}% · late {late:.1f}% · corrupt {corrupt:.1f}% · "
                    f"profile v{profile_version} · as of {as_of_ts}",
                    className="curve-pub-meta",
                ),
            ],
        ),
        html.P(_KPI_LEAD, className="curve-section-lead"),
        html.Div(
            className="curve-outcome-row",
            children=[
                _outcome_card(
                    "Completeness",
                    f"{completeness:.1f}%",
                    variant="" if completeness >= 95 else "curve-outcome-warn",
                ),
                _outcome_card(
                    "Corrupt reads",
                    f"{corrupt:.1f}%",
                    variant="" if corrupt < 2 else "curve-outcome-warn",
                ),
                _outcome_card("Imputed intervals", str(imputed)),
                _outcome_card("BTM PV deducted", f"{btm_mwh:,.1f} MWh"),
            ],
        ),
        ucp.capability_section(
            "Net load profile",
            _WIDGET_NET_LOAD,
            dcc.Graph(
                figure=_net_load_chart(
                    [[r[0], r[1], r[3]] for r in (prof_res.rows if prof_res.ok else [])]
                ),
                config={"displayModeBar": False},
            ),
        ),
        ucp.capability_section(
            "Behind-the-meter PV",
            _WIDGET_BTM,
            dcc.Graph(
                figure=_btm_chart(
                    [[r[0], r[2], r[3]] for r in (prof_res.rows if prof_res.ok else [])],
                    [[r[0], r[1]] for r in (btm_ts_res.rows if btm_ts_res.ok else [])],
                ),
                config={"displayModeBar": False},
            ),
        ),
        ucp.capability_section(
            "Quality grid",
            _WIDGET_QUALITY,
            _table(
                ["Zone", "Segment", "Complete %", "Late %", "Corrupt %", "Imputed", "Status"],
                grid_res.rows if grid_res.ok and grid_res.rows else [],
            )
            if grid_res.ok and grid_res.rows
            else html.P("No quality rows for this filter.", className="curve-muted"),
        ),
        html.P(
            f"Snapshot for {delivery_date}. Synthetic meters; aggregated above k-anonymity.",
            className="curve-footnote",
        ),
    ]
    return html.Div(className="curve-page-body", children=parts)


@callback(
    Output("vf-sm-date", "options"),
    Output("vf-sm-date", "value"),
    Output("vf-sm-zone", "options"),
    Output("vf-sm-zone", "value"),
    Output("vf-sm-segment", "options"),
    Output("vf-sm-segment", "value"),
    Input("sql-warehouse-dropdown", "value"),
    Input("vf-sm-refresh", "n_clicks"),
    State("vf-sm-date", "value"),
    State("vf-sm-zone", "value"),
    State("vf-sm-segment", "value"),
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
    Output("vf-sm-body", "children"),
    Input("sql-warehouse-dropdown", "value"),
    Input("vf-sm-date", "value"),
    Input("vf-sm-zone", "value"),
    Input("vf-sm-segment", "value"),
    Input("vf-sm-refresh", "n_clicks"),
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
        probe = ucp.run_uc_sql(warehouse_id, f"SELECT COUNT(*) FROM {ucp.fq('volume_forecast_gold_metering_quality')}")
        if probe.ok and probe.rows and int(float(probe.rows[0][0])) > 0:
            return _alert("Delivery dates could not be loaded — choose Refresh.", kind="warn")
        return _alert("No smart-metering data. Run `energy_trading_demo_data`, then select a connection.", kind="warn")
    return _body(
        warehouse_id,
        ucp.normalize_as_of(delivery_date) or delivery_date,
        zone or "ALL",
        segment or "ALL",
    )


@callback(
    Output("vf-sm-presenter-modal", "className"),
    Input("vf-sm-presenter-tip-btn", "n_clicks"),
    Input("vf-sm-presenter-close", "n_clicks"),
    Input("vf-sm-presenter-backdrop", "n_clicks"),
    State("vf-sm-presenter-modal", "className"),
    prevent_initial_call=True,
)
def _toggle_presenter(_o, _c, _b, current: str | None):
    base = "curve-presenter-modal"
    return base if current and "curve-presenter-modal-open" in current else f"{base} curve-presenter-modal-open"
