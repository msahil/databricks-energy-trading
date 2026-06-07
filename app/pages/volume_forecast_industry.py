"""
Industry Involvement — industrial baseline and demand-side flexibility.
Spec: modules/volume-forecasting/specifications/03-industry-involvement.md
"""

from __future__ import annotations

from typing import Any

import dash
from dash import Input, Output, State, callback, dcc, html
import plotly.graph_objects as go

import uc_pages as ucp
import ui_icons as uicons

_PATH = "/volume-forecasting/industry"

dash.register_page(
    __name__,
    path=_PATH,
    name="Industry Involvement",
    title="Industry Involvement — Volume forecasting",
)

_PAGE_TITLE = "Industry Involvement"
_PAGE_SUMMARY = (
    "A handful of large industrial sites can swing the zonal balance. Forecast each site's "
    "production-driven baseline, compare to metered actuals, and quantify dispatchable "
    "flexibility — the MW the DSR desk can bid into balancing markets."
)

_KPI_LEAD = (
    "Industrial footprint for the selected day: total baseline load, flexible capacity up and down, "
    "and typical activation price."
)
_WIDGET_LOAD = (
    "Baseline vs metered actual — production schedules drive the baseline; deviations flag "
    "sites running hot or in maintenance."
)
_WIDGET_FLEX = (
    "Dispatchable flexibility by site and product (shift, shed, boost). "
    "Feeds the short-term DSR bid stack."
)
_WIDGET_SITES = (
    "Site registry: industry, contracted capacity, driver type, and current availability."
)

_PRESENTER_LEAD = ucp.PRESENTER_LEAD_CAPABILITY

_PRESENTER_SECTIONS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "1 — Pain point for traders",
        (
            "A single smelter, chemical park, or hyperscale data centre can move more megawatts than thousands of "
            "homes — yet many forecasting stacks bury industry inside residential load. Traders miss baseline nomination "
            "risk and miss flex revenue at the same time.",
            "When a large site deviates from its production schedule, nominations slip and imbalance cash-out hits "
            "before anyone locates the site in a spreadsheet. Balancing calls the account manager; trading blames "
            "the forecast.",
            "The DSR desk cannot bid flex it cannot see. Aggregators need baseline megawatts, available up and down, "
            "activation price, and minimum duration in one governed view — not a CRM export emailed at gate minus thirty.",
        ),
    ),
    (
        "2 — Business problem this solves",
        (
            "Industry involvement treats large sites as a first-class segment: baseline forecast from production "
            "schedules, flexibility harvested when market prices justify shed, shift, or boost products.",
            "Flexible megawatts on this page feed the short-term DSR bid stack; volume forecasting sizes the baseline, "
            "DSR activates the envelope when prices justify it. Industrial baseline rolls into published net volume "
            "demand — the squaring desk sees one official demand leg.",
            "Say with confidence: \"We forecast the plant's draw and its flex envelope on the same platform — DSR "
            "monetises the envelope when the market pays for it.\"",
        ),
    ),
    (
        "3 — This page and each widget",
        (
            "Page title and summary: Industry Involvement — for account managers, forecast analysts, and the VPP desk "
            "managing large contracted loads.",
            "Toolbar: Delivery date, industry type, and site filters. Drill to one named site when telling an "
            "account-manager story; return to fleet view for portfolio narrative.",
            "Status banner: Fleet headline, count of sites in WATCH, and total contracted megawatts — the shift-level "
            "scan before you open charts.",
            "Desk KPI cards: Baseline P50, aggregate flex up, aggregate flex down, and sites armed near delivery. "
            "Frame these as \"how much load\" and \"how much flex we can trade today.\"",
            "Site load versus baseline chart: Actual draw compared to scheduled production baseline by interval. "
            "Deviation is nomination and imbalance risk — say which intervals look exposed.",
            "Flexibility envelope chart: Available megawatts up for boost and down for shed or shift, with activation "
            "euros per megawatt-hour and minimum duration. This is the commercial envelope DSR bids from.",
            "Site registry table: Industry type, contracted capacity, driver type, and current availability — proves "
            "site-level governance rolls up to zonal forecasts.",
            "Close with conviction: \"Industry moves the book in chunks — baseline here, flex activation on DSR, both "
            "legs reconciled in publication before the prompt desk squares.\"",
        ),
    ),
)

_PRODUCT_COLORS = {"SHIFT": "#2563eb", "SHED": "#ea580c", "BOOST": "#16a34a"}


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


def _dim_pred(zone: str, industry: str, site: str) -> str:
    parts: list[str] = []
    if zone and zone != "ALL":
        parts.append(f"zone_code = '{ucp.sql_escape(zone)}'")
    if industry and industry != "ALL":
        parts.append(f"industry = '{ucp.sql_escape(industry)}'")
    if site and site != "ALL":
        parts.append(f"site_id = '{ucp.sql_escape(site)}'")
    return (" AND " + " AND ".join(parts)) if parts else ""


def _load_chart(rows: list[list[Any]]) -> go.Figure:
    """Baseline vs actual over the day (aggregated or single site)."""
    fig = go.Figure()
    if not rows:
        fig.update_layout(template="plotly_white", height=340, margin=ucp.plotly_chart_margins(n_traces=2))
        return fig

    xs, baseline, actual = [], [], []
    for row in rows:
        xs.append(str(row[0]))
        baseline.append(float(row[1] or 0))
        actual.append(_opt_float(row[2]))

    fig.add_trace(go.Scatter(x=xs, y=baseline, name="Baseline", line=dict(color="#94a3b8", width=2)))
    if any(v is not None for v in actual):
        fig.add_trace(
            go.Scatter(
                x=xs,
                y=[v if v is not None else None for v in actual],
                name="Actual",
                line=dict(color="#2563eb", width=2),
                mode="lines+markers",
                marker=dict(size=4),
            )
        )
    n_traces = 2 if any(v is not None for v in actual) else 1
    fig.update_layout(
        yaxis_title="MW",
        template="plotly_white",
        height=340,
        margin=ucp.plotly_chart_margins(n_traces=n_traces),
        xaxis_tickangle=-45,
        legend=ucp.plotly_legend(n_traces=n_traces),
    )
    return fig


def _flex_chart(rows: list[list[Any]]) -> go.Figure:
    """Grouped bars: flexible down (and up) by site, coloured by product."""
    fig = go.Figure()
    if not rows:
        fig.update_layout(template="plotly_white", height=300, margin=ucp.plotly_chart_margins(n_traces=2))
        return fig

    sites = sorted({str(r[0]) for r in rows})
    products = sorted({str(r[1]) for r in rows})
    down_by: dict[tuple[str, str], float] = {}
    up_by: dict[tuple[str, str], float] = {}
    for row in rows:
        key = (str(row[0]), str(row[1]))
        down_by[key] = float(row[2] or 0)
        up_by[key] = float(row[3] or 0)

    for product in products:
        downs = [down_by.get((s, product), 0) for s in sites]
        ups = [up_by.get((s, product), 0) for s in sites]
        color = _PRODUCT_COLORS.get(product, "#64748b")
        fig.add_trace(go.Bar(name=f"{product} down", x=sites, y=downs, marker_color=color))
        if any(ups):
            fig.add_trace(
                go.Bar(
                    name=f"{product} up",
                    x=sites,
                    y=ups,
                    marker_color=color,
                    marker_pattern_shape="/",
                    opacity=0.75,
                )
            )

    n_traces = len(products) * (2 if any(up_by.values()) else 1)
    fig.update_layout(
        barmode="group",
        yaxis_title="MW",
        template="plotly_white",
        height=300,
        margin=ucp.plotly_chart_margins(n_traces=min(n_traces, 4)),
        legend=ucp.plotly_legend(n_traces=min(n_traces, 4)),
        xaxis_tickangle=-25,
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
                                    html.Span("Industrial & DSR", className="curve-page-badge"),
                                ],
                            ),
                            ucp.presenter_tip_button("vf-ind-presenter-tip-btn"),
                        ],
                    ),
                    uicons.hero_title(_PAGE_TITLE, uicons.VOLUME_FORECAST_NAV_ICONS[_PATH]),
                    html.P(_PAGE_SUMMARY, className="curve-page-summary"),
                ],
            ),
            ucp.presenter_modal(
                _PRESENTER_SECTIONS,
                modal_id="vf-ind-presenter-modal",
                close_id="vf-ind-presenter-close",
                backdrop_id="vf-ind-presenter-backdrop",
                title_id="vf-ind-presenter-modal-title",
                lead=_PRESENTER_LEAD,
            ),
            html.Div(
                className="curve-callout curve-callout-accent",
                children=html.P(
                    "Flexible MW rolls into the short-term DSR bid stack. "
                    "Industrial baseline rolls into net-volume reconciliation (07).",
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
                                id="vf-ind-date",
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
                                id="vf-ind-zone",
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
                            html.Label("Industry", className="curve-toolbar-label"),
                            dcc.Dropdown(
                                id="vf-ind-industry",
                                options=[{"label": "All industries", "value": "ALL"}],
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
                            html.Label("Site", className="curve-toolbar-label"),
                            dcc.Dropdown(
                                id="vf-ind-site",
                                options=[{"label": "All sites", "value": "ALL"}],
                                value="ALL",
                                clearable=False,
                                className="toolbar-select st-toolbar-zone",
                                optionHeight=44,
                            ),
                        ],
                    ),
                    html.Button("Refresh", id="vf-ind-refresh", type="button", className="curve-refresh-btn"),
                ],
            ),
            dcc.Loading(id="vf-ind-loading", type="default", children=html.Div(id="vf-ind-body")),
        ],
    )


def _body(warehouse_id: str, delivery_date: str, zone: str, industry: str, site: str) -> html.Div:
    dp = ucp.sql_delivery_date_predicate("delivery_date", delivery_date)
    dim_pred = _dim_pred(zone, industry, site)
    load_parts = []
    if zone != "ALL":
        load_parts.append(f"l.zone_code = '{ucp.sql_escape(zone)}'")
    if industry != "ALL":
        load_parts.append(f"d.industry = '{ucp.sql_escape(industry)}'")
    if site != "ALL":
        load_parts.append(f"l.site_id = '{ucp.sql_escape(site)}'")
    load_filter = (" AND " + " AND ".join(load_parts)) if load_parts else ""

    flex_parts = []
    if zone != "ALL":
        flex_parts.append(f"f.zone_code = '{ucp.sql_escape(zone)}'")
    if site != "ALL":
        flex_parts.append(f"f.site_id = '{ucp.sql_escape(site)}'")
    if industry != "ALL":
        flex_parts.append(f"d.industry = '{ucp.sql_escape(industry)}'")
    flex_filter = (" AND " + " AND ".join(flex_parts)) if flex_parts else ""

    kpi_sql = f"""
    SELECT
        ROUND(AVG(interval_base), 1) AS avg_baseline_mw,
        ROUND(AVG(interval_flex_up), 1) AS avg_flex_up_mw,
        ROUND(AVG(interval_flex_down), 1) AS avg_flex_down_mw,
        ROUND(AVG(activation_price_eur_mwh), 1) AS avg_price
    FROM (
        SELECT l.interval_start,
               SUM(l.baseline_mw) AS interval_base,
               COALESCE(SUM(f.flexible_up_mw), 0) AS interval_flex_up,
               COALESCE(SUM(f.flexible_down_mw), 0) AS interval_flex_down,
               AVG(f.activation_price_eur_mwh) AS activation_price_eur_mwh
        FROM {ucp.fq("volume_forecast_silver_industrial_load")} l
        LEFT JOIN {ucp.fq("volume_forecast_dim_industrial_sites")} d ON l.site_id = d.site_id
        LEFT JOIN {ucp.fq("volume_forecast_gold_industrial_flexibility")} f
          ON l.site_id = f.site_id AND l.interval_start = f.interval_start AND l.delivery_date = f.delivery_date
        WHERE {dp}{load_filter}
        GROUP BY l.interval_start
    )
    """
    kpi_res = ucp.run_uc_sql(warehouse_id, kpi_sql)

    armed_sql = f"""
    SELECT COUNT(DISTINCT f.site_id) AS n_armed
    FROM {ucp.fq("volume_forecast_gold_industrial_flexibility")} f
    LEFT JOIN {ucp.fq("volume_forecast_dim_industrial_sites")} d ON f.site_id = d.site_id
    WHERE {dp} AND f.availability_status = 'ARMED'{flex_filter}
    """
    armed_res = ucp.run_uc_sql(warehouse_id, armed_sql)

    if not kpi_res.ok:
        return _alert(f"Could not load industrial KPIs: {kpi_res.error}", kind="error")
    if not kpi_res.rows:
        return _alert("No industrial load data for this filter.", kind="warn")

    k = dict(zip(kpi_res.columns, kpi_res.rows[0]))
    baseline = float(k.get("avg_baseline_mw") or 0)
    flex_up = float(k.get("avg_flex_up_mw") or 0)
    flex_down = float(k.get("avg_flex_down_mw") or 0)
    avg_price = float(k.get("avg_price") or 0)
    n_armed = int(float(armed_res.rows[0][0] or 0)) if armed_res.ok and armed_res.rows else 0

    load_sql = f"""
    SELECT l.interval_start,
           ROUND(SUM(l.baseline_mw), 2),
           ROUND(SUM(l.actual_mw), 2)
    FROM {ucp.fq("volume_forecast_silver_industrial_load")} l
    LEFT JOIN {ucp.fq("volume_forecast_dim_industrial_sites")} d ON l.site_id = d.site_id
    WHERE {dp}{load_filter}
    GROUP BY l.interval_start
    ORDER BY l.interval_start
    """
    load_res = ucp.run_uc_sql(warehouse_id, load_sql)

    flex_sql = f"""
    SELECT f.site_id, f.flex_product,
           ROUND(AVG(f.flexible_down_mw), 1),
           ROUND(AVG(f.flexible_up_mw), 1)
    FROM {ucp.fq("volume_forecast_gold_industrial_flexibility")} f
    LEFT JOIN {ucp.fq("volume_forecast_dim_industrial_sites")} d ON f.site_id = d.site_id
    WHERE {dp}{flex_filter}
    GROUP BY f.site_id, f.flex_product
    ORDER BY f.site_id, f.flex_product
    """
    flex_res = ucp.run_uc_sql(warehouse_id, flex_sql)

    site_sql = f"""
    SELECT d.site_id, d.site_name, d.industry, d.zone_code,
           d.contracted_mw, d.driver_type, d.is_flexible,
           COALESCE(flex.availability_status, 'N/A') AS availability_status,
           COALESCE(flex.flex_product, '—') AS flex_product,
           ROUND(COALESCE(flex.avg_price, 0), 1) AS avg_price
    FROM {ucp.fq("volume_forecast_dim_industrial_sites")} d
    LEFT JOIN (
        SELECT site_id,
               MAX(availability_status) AS availability_status,
               MAX(flex_product) AS flex_product,
               AVG(activation_price_eur_mwh) AS avg_price
        FROM {ucp.fq("volume_forecast_gold_industrial_flexibility")}
        WHERE {dp}
        GROUP BY site_id
    ) flex ON d.site_id = flex.site_id
    WHERE 1=1{dim_pred.replace('zone_code', 'd.zone_code').replace('industry', 'd.industry').replace('site_id', 'd.site_id') if dim_pred else ''}
    ORDER BY d.zone_code, d.contracted_mw DESC
    """
    site_res = ucp.run_uc_sql(warehouse_id, site_sql)

    parts: list[Any] = [
        html.Div(
            className="curve-publication-banner curve-pub-draft",
            children=[
                html.Span(f"{n_armed} armed" if n_armed else "No sites armed", className="curve-pub-badge"),
                html.Span(
                    f"Industrial baseline ≈ {baseline:.1f} MW · flex down {flex_down:.1f} MW / up {flex_up:.1f} MW",
                    className="curve-pub-headline",
                ),
                html.Span(f"Delivery {delivery_date}", className="curve-pub-meta"),
            ],
        ),
        html.P(_KPI_LEAD, className="curve-section-lead"),
        html.Div(
            className="curve-outcome-row",
            children=[
                _outcome_card("Avg baseline", f"{baseline:.1f} MW"),
                _outcome_card("Flexible down", f"{flex_down:.1f} MW"),
                _outcome_card("Flexible up", f"{flex_up:.1f} MW"),
                _outcome_card("Avg activation price", f"€{avg_price:.0f}/MWh"),
            ],
        ),
        ucp.capability_section(
            "Site load",
            _WIDGET_LOAD,
            dcc.Graph(
                figure=_load_chart(load_res.rows if load_res.ok else []),
                config={"displayModeBar": False},
            ),
        ),
        ucp.capability_section(
            "Flexibility stack",
            _WIDGET_FLEX,
            dcc.Graph(
                figure=_flex_chart(flex_res.rows if flex_res.ok else []),
                config={"displayModeBar": False},
            ),
        ),
        ucp.capability_section(
            "Site registry",
            _WIDGET_SITES,
            _table(
                ["Site", "Name", "Industry", "Zone", "Contracted MW", "Driver", "Flexible", "Status", "Product", "€/MWh"],
                [
                    [
                        r[0], r[1], r[2], r[3],
                        f"{float(r[4]):.0f}",
                        r[5],
                        "Yes" if str(r[6]).lower() in ("true", "1") else "No",
                        r[7], r[8], r[9],
                    ]
                    for r in (site_res.rows if site_res.ok else [])
                ],
            )
            if site_res.ok and site_res.rows
            else html.P("No sites match this filter.", className="curve-muted"),
        ),
        html.P(f"Snapshot for {delivery_date}. Synthetic site telemetry.", className="curve-footnote"),
    ]
    return html.Div(className="curve-page-body", children=parts)


@callback(
    Output("vf-ind-date", "options"),
    Output("vf-ind-date", "value"),
    Output("vf-ind-zone", "options"),
    Output("vf-ind-zone", "value"),
    Output("vf-ind-industry", "options"),
    Output("vf-ind-industry", "value"),
    Output("vf-ind-site", "options"),
    Output("vf-ind-site", "value"),
    Input("sql-warehouse-dropdown", "value"),
    Input("vf-ind-refresh", "n_clicks"),
    State("vf-ind-date", "value"),
    State("vf-ind-zone", "value"),
    State("vf-ind-industry", "value"),
    State("vf-ind-site", "value"),
    prevent_initial_call=False,
)
def _load_filters(
    warehouse_id: str | None,
    _n: int | None,
    current_date: str | None,
    current_zone: str | None,
    current_industry: str | None,
    current_site: str | None,
):
    zone_opts = [{"label": "All zones", "value": "ALL"}]
    ind_opts = [{"label": "All industries", "value": "ALL"}]
    site_opts = [{"label": "All sites", "value": "ALL"}]
    if not warehouse_id:
        return (
            [], None,
            zone_opts, ucp.resolve_dropdown_value(current_zone, ["ALL"]),
            ind_opts, ucp.resolve_dropdown_value(current_industry, ["ALL"]),
            site_opts, ucp.resolve_dropdown_value(current_site, ["ALL"]),
        )

    dates_sql = f"""
    SELECT DISTINCT delivery_date FROM {ucp.fq("volume_forecast_silver_industrial_load")}
    ORDER BY delivery_date DESC LIMIT 30
    """
    zones_sql = f"SELECT zone_code, country FROM {ucp.fq('volume_forecast_dim_zones')} ORDER BY zone_code"
    ind_sql = f"SELECT DISTINCT industry FROM {ucp.fq('volume_forecast_dim_industrial_sites')} ORDER BY industry"
    site_sql = f"SELECT site_id, site_name FROM {ucp.fq('volume_forecast_dim_industrial_sites')} ORDER BY site_id"

    d_res = ucp.run_uc_sql(warehouse_id, dates_sql)
    z_res = ucp.run_uc_sql(warehouse_id, zones_sql)
    i_res = ucp.run_uc_sql(warehouse_id, ind_sql)
    s_res = ucp.run_uc_sql(warehouse_id, site_sql)

    dates = [ucp.normalize_as_of(r[0]) for r in (d_res.rows if d_res.ok else []) if ucp.normalize_as_of(r[0])]
    date_opts = [{"label": d, "value": d} for d in dates]

    if z_res.ok:
        zone_opts += [{"label": f"{r[0]} — {r[1]}", "value": str(r[0])} for r in z_res.rows]
    if i_res.ok:
        ind_opts += [{"label": str(r[0]).replace("_", " ").title(), "value": str(r[0])} for r in i_res.rows]
    if s_res.ok:
        site_opts += [{"label": f"{r[0]} — {r[1]}", "value": str(r[0])} for r in s_res.rows]

    zone_values = [str(o["value"]) for o in zone_opts]
    ind_values = [str(o["value"]) for o in ind_opts]
    site_values = [str(o["value"]) for o in site_opts]
    return (
        date_opts,
        ucp.resolve_dropdown_value(current_date, dates),
        zone_opts,
        ucp.resolve_dropdown_value(current_zone, zone_values),
        ind_opts,
        ucp.resolve_dropdown_value(current_industry, ind_values),
        site_opts,
        ucp.resolve_dropdown_value(current_site, site_values),
    )


@callback(
    Output("vf-ind-body", "children"),
    Input("sql-warehouse-dropdown", "value"),
    Input("vf-ind-date", "value"),
    Input("vf-ind-zone", "value"),
    Input("vf-ind-industry", "value"),
    Input("vf-ind-site", "value"),
    Input("vf-ind-refresh", "n_clicks"),
)
def _render_body(
    warehouse_id: str | None,
    delivery_date: str | None,
    zone: str | None,
    industry: str | None,
    site: str | None,
    _n: int | None,
):
    if not warehouse_id:
        return ucp.warehouse_prompt()
    if not delivery_date:
        probe = ucp.run_uc_sql(warehouse_id, f"SELECT COUNT(*) FROM {ucp.fq('volume_forecast_silver_industrial_load')}")
        if probe.ok and probe.rows and int(float(probe.rows[0][0])) > 0:
            return _alert("Delivery dates could not be loaded — choose Refresh.", kind="warn")
        return _alert("No industrial data. Run `energy_trading_demo_data`, then select a connection.", kind="warn")
    return _body(
        warehouse_id,
        ucp.normalize_as_of(delivery_date) or delivery_date,
        zone or "ALL",
        industry or "ALL",
        site or "ALL",
    )


@callback(
    Output("vf-ind-presenter-modal", "className"),
    Input("vf-ind-presenter-tip-btn", "n_clicks"),
    Input("vf-ind-presenter-close", "n_clicks"),
    Input("vf-ind-presenter-backdrop", "n_clicks"),
    State("vf-ind-presenter-modal", "className"),
    prevent_initial_call=True,
)
def _toggle_presenter(_o, _c, _b, current: str | None):
    base = "curve-presenter-modal"
    return base if current and "curve-presenter-modal-open" in current else f"{base} curve-presenter-modal-open"
