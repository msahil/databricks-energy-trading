"""
Publication & Net-Volume Reconciliation — official governed net volume.
Spec: modules/volume-forecasting/specifications/07-publication-net-volume.md
"""

from __future__ import annotations

from typing import Any

import dash
from dash import Input, Output, State, callback, dcc, html
import plotly.graph_objects as go

import uc_pages as ucp
import ui_icons as uicons

_PATH = "/volume-forecasting/publication"

dash.register_page(
    __name__,
    path=_PATH,
    name="Publication & Net Volume",
    title="Publication & Net Volume — Volume forecasting",
)

_PAGE_TITLE = "Publication & Net Volume"
_PAGE_SUMMARY = (
    "Reconcile demand legs (01–03) and supply legs (05–06) into one official, versioned net volume "
    "per zone per interval — the single source of truth every desk trades on. Published cuts are "
    "immutable, carry an as-of and status, and supersede prior vintages with a full audit trail."
)

_KPI_LEAD = (
    "Official cut for the selected version: net position, demand and supply totals, and revision "
    "since the prior published version."
)
_WIDGET_NET = (
    "Signed net volume by interval — demand minus supply. This is the number desks square against."
)
_WIDGET_STACK = (
    "Legs behind the net — consumption, industrial, wind, and utility-scale solar. "
    "BTM PV (dashed) is netted in demand via Smart Metering and is not added to supply."
)
_WIDGET_REVISION = (
    "How the official net moved versus the prior published cut (`revision_mw`)."
)
_WIDGET_HANDOFF = (
    "Downstream consumers of the published volume — cadence, SLA, and version each last read."
)

_PRESENTER_LEAD = ucp.PRESENTER_LEAD_CAPABILITY

_PRESENTER_SECTIONS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "1 — Pain point for traders",
        (
            "On a busy morning every desk can claim a different net megawatt — wind in one file, demand in another, "
            "solar in an email attachment — and the squaring desk does not know which number is official when the gate "
            "is closing.",
            "Without version and as-of timestamp, risk cannot explain yesterday's imbalance to finance; auditors cannot "
            "reconstruct what was published at ten o'clock versus what was draft at nine.",
            "Double-counting rooftop PV or omitting a forecast leg is not a back-office mistake — it becomes real "
            "imbalance cash-out when nominations were built on the wrong net volume.",
        ),
    ),
    (
        "2 — Business problem this solves",
        (
            "Publication reconciles demand and supply legs into one governed net volume with version, as-of, and a "
            "completeness gate. Downstream trading, risk, and reporting consume this cut — not raw capability tables.",
            "Published versions are immutable; supersessions are auditable with Delta time travel. Behind-the-meter "
            "PV stays in demand; utility-scale wind and solar sit in supply — rules enforced before status moves to "
            "PUBLISHED.",
            "This is the handoff point between forecasting and trading. Say clearly: \"This is the only megawatt count "
            "the prompt desk squares — everything else is draft until it passes this gate.\"",
        ),
    ),
    (
        "3 — This page and each widget",
        (
            "Page title and summary: Publication and Net Volume — the official reconciled cut. Position this after wind, "
            "solar, and consumption in the demo flow so legs are familiar before you show reconciliation.",
            "Toolbar: Delivery date and zone — keep the same date you used on wind, solar, consumption, and "
            "near-delivery so traders hear one coherent delivery-day story.",
            "Status banner: Read version number and as-of timestamp aloud — experienced traders respect official cuts. "
            "Completeness PASS or FAIL tells you whether all legs were present. Publish status PUBLISHED versus DRAFT "
            "tells you whether downstream systems should consume the cut.",
            "Desk KPI cards: Net volume P50, demand leg total, supply leg total, and revision count since the prior "
            "publish — the executive scan before you open charts.",
            "Net volume chart: Single reconciled curve interval by interval — explicitly say this is the line the "
            "squaring desk uses, not a forecaster's draft.",
            "Leg stack chart: Demand and supply components stacked to show how net is composed. Use it when someone "
            "asks \"where did the megawatts go?\"",
            "Revision strip: Delta since the last official version — narrate what changed when the latest weather run "
            "landed. This is the publish-gate story forecasters live through.",
            "Consumer handoff table: Downstream systems, read cadence, SLA, and last version consumed — proves "
            "enterprise integration, not a standalone dashboard.",
            "Close with conviction: \"Wind and solar forecast the legs; this page signs the number — near-delivery and "
            "risk consume nothing else for official position.\"",
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


def _zone_pred(zone: str, *, alias: str = "") -> str:
    col = f"{alias}zone_code" if alias else "zone_code"
    if zone and zone != "ALL":
        return f" AND {col} = '{ucp.sql_escape(zone)}'"
    return ""


def _net_chart(rows: list[list[Any]]) -> go.Figure:
    fig = go.Figure()
    if not rows:
        fig.update_layout(template="plotly_white", height=340, margin=ucp.plotly_chart_margins(n_traces=1))
        return fig

    xs, ys, colors = [], [], []
    for row in rows:
        xs.append(str(row[0]))
        net = float(row[1] or 0)
        ys.append(net)
        colors.append("#2563eb" if net >= 0 else "#dc2626")

    fig.add_trace(
        go.Bar(
            x=xs,
            y=ys,
            marker_color=colors,
            name="Net volume",
            hovertemplate="%{x}<br>Net %{y:.2f} MW<extra></extra>",
        )
    )
    fig.update_layout(
        yaxis_title="MW",
        template="plotly_white",
        height=340,
        margin=ucp.plotly_chart_margins(n_traces=1),
        xaxis_tickangle=-45,
        showlegend=False,
    )
    return fig


def _stack_chart(rows: list[list[Any]]) -> go.Figure:
    fig = go.Figure()
    if not rows:
        fig.update_layout(template="plotly_white", height=360, margin=ucp.plotly_chart_margins(n_traces=5))
        return fig

    xs: list[str] = []
    legs: dict[str, list[float]] = {
        "Consumption (ST)": [],
        "Industrial": [],
        "Wind": [],
        "Solar": [],
        "BTM PV (netted)": [],
    }
    for row in rows:
        xs.append(str(row[0]))
        legs["Consumption (ST)"].append(float(row[1] or 0))
        legs["Industrial"].append(float(row[2] or 0))
        legs["Wind"].append(float(row[3] or 0))
        legs["Solar"].append(float(row[4] or 0))
        legs["BTM PV (netted)"].append(float(row[5] or 0))

    palette = {
        "Consumption (ST)": "#2563eb",
        "Industrial": "#7c3aed",
        "Wind": "#059669",
        "Solar": "#d97706",
    }
    for name in ("Consumption (ST)", "Industrial", "Wind", "Solar"):
        fig.add_trace(
            go.Scatter(
                x=xs,
                y=legs[name],
                name=name,
                stackgroup="legs",
                mode="lines",
                line=dict(width=0.5, color=palette[name]),
                fillcolor=palette[name],
            )
        )
    fig.add_trace(
        go.Scatter(
            x=xs,
            y=legs["BTM PV (netted)"],
            name="BTM PV (netted)",
            line=dict(color="#6366f1", width=1.5, dash="dot"),
            mode="lines",
        )
    )
    fig.update_layout(
        yaxis_title="MW",
        template="plotly_white",
        height=360,
        margin=ucp.plotly_chart_margins(n_traces=5),
        xaxis_tickangle=-45,
        legend=ucp.plotly_legend(n_traces=5),
    )
    return fig


def _revision_chart(rows: list[list[Any]]) -> go.Figure:
    fig = go.Figure()
    if not rows:
        fig.update_layout(template="plotly_white", height=260, margin=ucp.plotly_chart_margins(n_traces=1))
        return fig

    xs, ys, colors = [], [], []
    for row in rows:
        rev = _opt_float(row[1])
        if rev is None:
            continue
        xs.append(str(row[0]))
        ys.append(rev)
        colors.append("#22c55e" if rev >= 0 else "#ef4444")

    if not xs:
        fig.update_layout(template="plotly_white", height=260, margin=ucp.plotly_chart_margins(n_traces=1))
        return fig

    fig.add_trace(
        go.Bar(
            x=xs,
            y=ys,
            marker_color=colors,
            hovertemplate="%{x}<br>Revision %{y:.2f} MW<extra></extra>",
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
                                    html.Span("Source of truth", className="curve-page-badge"),
                                ],
                            ),
                            ucp.presenter_tip_button("vf-pub-presenter-tip-btn"),
                        ],
                    ),
                    uicons.hero_title(_PAGE_TITLE, uicons.VOLUME_FORECAST_NAV_ICONS[_PATH]),
                    html.P(_PAGE_SUMMARY, className="curve-page-summary"),
                ],
            ),
            ucp.presenter_modal(
                _PRESENTER_SECTIONS,
                modal_id="vf-pub-presenter-modal",
                close_id="vf-pub-presenter-close",
                backdrop_id="vf-pub-presenter-backdrop",
                title_id="vf-pub-presenter-modal-title",
                lead=_PRESENTER_LEAD,
            ),
            html.Div(
                className="curve-callout curve-callout-accent",
                children=html.P(
                    "Desks read published net volume — not raw capability outputs. "
                    "Only the latest PUBLISHED version is the official cut unless you deliberately compare an older one.",
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
                                id="vf-pub-date",
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
                                id="vf-pub-zone",
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
                            html.Label("Publication version", className="curve-toolbar-label"),
                            dcc.Dropdown(
                                id="vf-pub-version",
                                options=[],
                                value=None,
                                clearable=False,
                                className="toolbar-select st-toolbar-zone",
                                optionHeight=44,
                            ),
                        ],
                    ),
                    html.Button("Refresh", id="vf-pub-refresh", type="button", className="curve-refresh-btn"),
                ],
            ),
            dcc.Loading(id="vf-pub-loading", type="default", children=html.Div(id="vf-pub-body")),
        ],
    )


def _body(warehouse_id: str, delivery_date: str, zone: str, version: int) -> html.Div:
    dp = ucp.sql_delivery_date_predicate("delivery_date", delivery_date)
    zp = _zone_pred(zone)

    log_sql = f"""
    SELECT publication_version, gate_status, published_ts, completeness_pct, legs_present, note,
           superseded_version
    FROM {ucp.fq("volume_forecast_gold_publication_log")}
    WHERE {dp}{zp} AND publication_version = {int(version)}
    LIMIT 1
    """
    if zone == "ALL":
        log_sql = f"""
        SELECT
            {int(version)} AS publication_version,
            MAX(CASE gate_status WHEN 'BLOCKED' THEN 3 WHEN 'DRAFT' THEN 2 ELSE 1 END) AS gate_rank,
            MAX(published_ts) AS published_ts,
            ROUND(MIN(completeness_pct), 1) AS completeness_pct,
            MIN(legs_present) AS legs_present,
            MAX(note) AS note,
            MAX(superseded_version) AS superseded_version
        FROM {ucp.fq("volume_forecast_gold_publication_log")}
        WHERE {dp} AND publication_version = {int(version)}
        """

    log_res = ucp.run_uc_sql(warehouse_id, log_sql)
    if not log_res.ok:
        return _alert(f"Could not load publication log: {log_res.error}", kind="error")
    if not log_res.rows:
        return _alert("No publication log for this filter.", kind="warn")

    log = dict(zip(log_res.columns, log_res.rows[0]))
    if zone == "ALL":
        gate_rank = int(float(log.get("gate_rank") or 1))
        gate_status = "BLOCKED" if gate_rank == 3 else "DRAFT" if gate_rank == 2 else "PUBLISHED"
    else:
        gate_status = str(log.get("gate_status") or "PUBLISHED")
    completeness = float(log.get("completeness_pct") or 0)
    legs_present = int(float(log.get("legs_present") or 0))
    published_ts = str(log.get("published_ts") or "—")
    note = str(log.get("note") or "")
    superseded = log.get("superseded_version")

    status_sql = f"""
    SELECT MAX(publication_status)
    FROM {ucp.fq("volume_forecast_gold_net_volume")}
    WHERE {dp}{zp} AND publication_version = {int(version)}
    """
    status_res = ucp.run_uc_sql(warehouse_id, status_sql)
    pub_status = str(status_res.rows[0][0] or gate_status) if status_res.ok and status_res.rows else gate_status

    kpi_sql = f"""
    SELECT
        ROUND(AVG(net_volume_mw), 2) AS avg_net,
        ROUND(MAX(ABS(net_volume_mw)), 2) AS peak_abs_net,
        ROUND(AVG(total_demand_mw), 2) AS avg_demand,
        ROUND(AVG(total_supply_mw), 2) AS avg_supply,
        ROUND(MAX(ABS(revision_mw)), 2) AS peak_revision,
        ROUND(AVG(revision_mw), 2) AS avg_revision,
        MAX(as_of_ts) AS as_of_ts
    FROM {ucp.fq("volume_forecast_gold_net_volume")}
    WHERE {dp}{zp} AND publication_version = {int(version)}
    """
    kpi_res = ucp.run_uc_sql(warehouse_id, kpi_sql)
    if not kpi_res.ok:
        return _alert(f"Could not load net volume: {kpi_res.error}", kind="error")
    if not kpi_res.rows:
        return _alert("No net volume rows for this version.", kind="warn")

    k = dict(zip(kpi_res.columns, kpi_res.rows[0]))
    avg_net = float(k.get("avg_net") or 0)
    peak_abs_net = float(k.get("peak_abs_net") or 0)
    avg_demand = float(k.get("avg_demand") or 0)
    avg_supply = float(k.get("avg_supply") or 0)
    peak_revision = float(k.get("peak_revision") or 0)
    avg_revision = float(k.get("avg_revision") or 0)
    as_of_ts = str(k.get("as_of_ts") or published_ts)

    net_sql = f"""
    SELECT interval_start, ROUND(SUM(net_volume_mw), 2)
    FROM {ucp.fq("volume_forecast_gold_net_volume")}
    WHERE {dp}{zp} AND publication_version = {int(version)}
    GROUP BY interval_start
    ORDER BY interval_start
    """
    net_res = ucp.run_uc_sql(warehouse_id, net_sql)

    stack_sql = f"""
    SELECT interval_start,
           ROUND(SUM(consumption_st_mw), 2),
           ROUND(SUM(industrial_mw), 2),
           ROUND(SUM(wind_mw), 2),
           ROUND(SUM(solar_mw), 2),
           ROUND(SUM(btm_pv_mw), 2)
    FROM {ucp.fq("volume_forecast_gold_net_volume")}
    WHERE {dp}{zp} AND publication_version = {int(version)}
    GROUP BY interval_start
    ORDER BY interval_start
    """
    stack_res = ucp.run_uc_sql(warehouse_id, stack_sql)

    rev_sql = f"""
    SELECT interval_start, ROUND(SUM(revision_mw), 2)
    FROM {ucp.fq("volume_forecast_gold_net_volume")}
    WHERE {dp}{zp} AND publication_version = {int(version)} AND revision_mw IS NOT NULL
    GROUP BY interval_start
    ORDER BY interval_start
    """
    rev_res = ucp.run_uc_sql(warehouse_id, rev_sql)

    handoff_sql = f"""
    SELECT consumer, zone_code, handoff_field, cadence, latest_version, sla_minutes
    FROM {ucp.fq("volume_forecast_gold_consumer_handoff")}
    WHERE 1=1{_zone_pred(zone)}
    ORDER BY consumer, zone_code
    """
    handoff_res = ucp.run_uc_sql(warehouse_id, handoff_sql)

    if pub_status == "PUBLISHED":
        banner_cls = "curve-pub-official"
    elif pub_status == "SUPERSEDED":
        banner_cls = "curve-pub-superseded"
    else:
        banner_cls = "curve-pub-draft"

    headline = (
        f"Official cut v{version} — all desks read this net volume"
        if pub_status == "PUBLISHED"
        else f"Version v{version} ({pub_status.lower()}) — not the live official cut"
        if pub_status == "SUPERSEDED"
        else f"Draft v{version} — gate {gate_status.lower()}"
    )

    parts: list[Any] = [
        html.Div(
            className=f"curve-publication-banner {banner_cls}",
            children=[
                html.Span(pub_status, className="curve-pub-badge"),
                html.Span(headline, className="curve-pub-headline"),
                html.Span(
                    f"v{version} · {legs_present}/5 legs · {completeness:.0f}% complete · as of {as_of_ts}"
                    + (f" · superseded v{superseded}" if superseded is not None and str(superseded).strip() else "")
                    + (f" · {note}" if note else ""),
                    className="curve-pub-meta",
                ),
            ],
        ),
        html.P(_KPI_LEAD, className="curve-section-lead"),
        html.Div(
            className="curve-outcome-row",
            children=[
                _outcome_card("Avg net volume", f"{avg_net:.1f} MW", sub=f"peak |net| {peak_abs_net:.1f} MW"),
                _outcome_card("Avg demand", f"{avg_demand:.1f} MW"),
                _outcome_card("Avg supply", f"{avg_supply:.1f} MW"),
                _outcome_card(
                    "Revision vs prior",
                    f"±{peak_revision:.2f} MW" if peak_revision else "—",
                    sub=f"avg Δ {avg_revision:.2f} MW" if avg_revision else "first cut",
                    variant="curve-outcome-warn" if peak_revision > 10 else "",
                ),
            ],
        ),
        ucp.capability_section(
            "Net volume",
            _WIDGET_NET,
            dcc.Graph(
                figure=_net_chart(net_res.rows if net_res.ok else []),
                config={"displayModeBar": False},
            ),
        ),
        ucp.capability_section(
            "Supply / demand legs",
            _WIDGET_STACK,
            dcc.Graph(
                figure=_stack_chart(stack_res.rows if stack_res.ok else []),
                config={"displayModeBar": False},
            ),
        ),
        ucp.capability_section(
            "Version diff",
            _WIDGET_REVISION,
            dcc.Graph(
                figure=_revision_chart(rev_res.rows if rev_res.ok else []),
                config={"displayModeBar": False},
            )
            if rev_res.ok and rev_res.rows
            else html.P("No revision — this is the first published cut for this version.", className="curve-muted"),
        ),
        ucp.capability_section(
            "Consumer handoff",
            _WIDGET_HANDOFF,
            _table(
                ["Consumer", "Zone", "Field", "Cadence", "Version", "SLA (min)"],
                [
                    [r[0], r[1], r[2], r[3], r[4], r[5]]
                    for r in (handoff_res.rows if handoff_res.ok else [])
                ],
            )
            if handoff_res.ok and handoff_res.rows
            else html.P("No consumer handoff rows.", className="curve-muted"),
        ),
        html.P(f"Publication v{version} for {delivery_date}.", className="curve-footnote"),
    ]
    return html.Div(className="curve-page-body", children=parts)


@callback(
    Output("vf-pub-date", "options"),
    Output("vf-pub-date", "value"),
    Output("vf-pub-zone", "options"),
    Output("vf-pub-zone", "value"),
    Output("vf-pub-version", "options"),
    Output("vf-pub-version", "value"),
    Input("sql-warehouse-dropdown", "value"),
    Input("vf-pub-refresh", "n_clicks"),
    Input("vf-pub-date", "value"),
    Input("vf-pub-zone", "value"),
    State("vf-pub-version", "value"),
    prevent_initial_call=False,
)
def _load_filters(warehouse_id, _n, delivery_date, zone, current_version):
    zone_opts = [{"label": "All zones", "value": "ALL"}]
    version_opts: list[dict[str, Any]] = []
    if not warehouse_id:
        return [], None, zone_opts, "ALL", [], None

    d_res = ucp.run_uc_sql(
        warehouse_id,
        f"""
        SELECT DISTINCT delivery_date
        FROM {ucp.fq("volume_forecast_gold_net_volume")}
        ORDER BY delivery_date DESC
        LIMIT 30
        """,
    )
    z_res = ucp.run_uc_sql(
        warehouse_id,
        f"SELECT zone_code, country FROM {ucp.fq('volume_forecast_dim_zones')} ORDER BY zone_code",
    )

    dates = [ucp.normalize_as_of(r[0]) for r in (d_res.rows if d_res.ok else []) if ucp.normalize_as_of(r[0])]
    resolved_date = ucp.resolve_dropdown_value(delivery_date, dates)

    if z_res.ok:
        zone_opts += [{"label": f"{r[0]} — {r[1]}", "value": str(r[0])} for r in z_res.rows]
    resolved_zone = ucp.resolve_dropdown_value(zone or "ALL", [o["value"] for o in zone_opts])

    if resolved_date:
        dp = ucp.sql_delivery_date_predicate("delivery_date", resolved_date)
        zp = _zone_pred(resolved_zone)
        v_res = ucp.run_uc_sql(
            warehouse_id,
            f"""
            SELECT publication_version, gate_status, published_ts
            FROM {ucp.fq("volume_forecast_gold_publication_log")}
            WHERE {dp}{zp}
            ORDER BY publication_version DESC
            """,
        )
        if v_res.ok:
            for row in v_res.rows:
                ver, gate, pts = int(float(row[0])), str(row[1]), str(row[2] or "")
                version_opts.append({"label": f"v{ver} — {gate} ({pts[:16]})", "value": ver})

    version_values = [o["value"] for o in version_opts]
    if current_version in version_values:
        resolved_version = current_version
    else:
        published = [o["value"] for o in version_opts if "PUBLISHED" in o["label"]]
        resolved_version = published[0] if published else (version_values[0] if version_values else None)

    return (
        [{"label": d, "value": d} for d in dates],
        resolved_date,
        zone_opts,
        resolved_zone,
        version_opts,
        resolved_version,
    )


@callback(
    Output("vf-pub-body", "children"),
    Input("sql-warehouse-dropdown", "value"),
    Input("vf-pub-date", "value"),
    Input("vf-pub-zone", "value"),
    Input("vf-pub-version", "value"),
    Input("vf-pub-refresh", "n_clicks"),
)
def _render_body(warehouse_id, delivery_date, zone, version, _n):
    if not warehouse_id:
        return ucp.warehouse_prompt()
    if not delivery_date:
        probe = ucp.run_uc_sql(warehouse_id, f"SELECT COUNT(*) FROM {ucp.fq('volume_forecast_gold_net_volume')}")
        if probe.ok and probe.rows and int(float(probe.rows[0][0])) > 0:
            return _alert("Delivery dates could not be loaded — choose Refresh.", kind="warn")
        return _alert(
            "No publication data. Run `energy_trading_demo_data` (needs capabilities 01–06 first), then select a connection.",
            kind="warn",
        )
    if version is None:
        return _alert("No publication version for this date/zone — choose Refresh.", kind="warn")
    return _body(
        warehouse_id,
        ucp.normalize_as_of(delivery_date) or delivery_date,
        zone or "ALL",
        int(version),
    )


@callback(
    Output("vf-pub-presenter-modal", "className"),
    Input("vf-pub-presenter-tip-btn", "n_clicks"),
    Input("vf-pub-presenter-close", "n_clicks"),
    Input("vf-pub-presenter-backdrop", "n_clicks"),
    State("vf-pub-presenter-modal", "className"),
    prevent_initial_call=True,
)
def _toggle_presenter(_o, _c, _b, current):
    base = "curve-presenter-modal"
    return base if current and "curve-presenter-modal-open" in current else f"{base} curve-presenter-modal-open"
