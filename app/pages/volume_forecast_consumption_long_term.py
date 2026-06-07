"""
Customer Consumption — Long Term — structural demand for the curve desk.
Spec: modules/volume-forecasting/specifications/02-customer-consumption-long-term.md
"""

from __future__ import annotations

from typing import Any

import dash
from dash import Input, Output, State, callback, dcc, html
import plotly.graph_objects as go

import uc_pages as ucp
import ui_icons as uicons

_PATH = "/volume-forecasting/consumption-long-term"

dash.register_page(
    __name__,
    path=_PATH,
    name="Customer Consumption — Long Term",
    title="Consumption · Long Term — Volume forecasting",
)

_PAGE_TITLE = "Customer Consumption — Long Term"
_PAGE_SUMMARY = (
    "Project structural demand months to years out for hedge sizing and PPA load shapes. "
    "Macro drivers and electrification scenarios bend the curve; P50 / P75 / P90 map to the "
    "layered hedge matrix the curve desk uses for Cal+1 through Cal+3."
)

_SEASON_ORDER = ("WINTER", "SPRING", "SUMMER", "AUTUMN")
_SCENARIO_LABELS = {
    "BASE": "Base",
    "HIGH_ELECTRIFICATION": "High electrification",
    "LOW_GROWTH": "Low growth",
}

_KPI_LEAD = (
    "Hedge-ready load shape for the selected scenario and horizon: baseload, peak, P90 layer, "
    "and how much electrification is adding to demand."
)
_WIDGET_SHAPE = (
    "Seasonal blocks by forecast year — P50 with P75 / P90 uncertainty bands. "
    "This is the shape origination sizes multi-year hedges against."
)
_WIDGET_SCENARIOS = (
    "How electrification bends the curve — compare base vs high-electrification paths "
    "at P50 for the selected year."
)
_WIDGET_DRIVERS = (
    "Assumptions behind the vintage: GDP growth, EV penetration, and heat-pump uptake. "
    "Reproducible via MLflow in production."
)

_PRESENTER_LEAD = ucp.PRESENTER_LEAD_CAPABILITY

_PRESENTER_SECTIONS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "1 — Pain point for traders",
        (
            "The curve desk must lock Cal+1 through Cal+3 hedges against a load shape that will not look like today's "
            "meter read. Electrification, heat pumps, and EV adoption rewrite winter and evening peaks over years — "
            "not over the next weather week.",
            "Teams that size purely on last year's profile carry gap risk when policy and customer behaviour move "
            "faster than the hedge matrix. Risk and retail planning will challenge every long-term megawatt curve with "
            "the same questions: show me the scenario, show me the band, show me which assumption moved it.",
            "Without governed scenarios and auditable vintages, origination defends hedges in slide decks while the "
            "prompt desk inherits the mistake at delivery.",
        ),
    ),
    (
        "2 — Business problem this solves",
        (
            "Long-term consumption anchors on governed Smart Metering history, then applies macro scenarios such as EV "
            "adoption and heat-pump penetration. This is structural trend forecasting — not tomorrow's temperature.",
            "P50, P75, and P90 map to how curve desks layer hedges across calendar years; baseload versus peakload "
            "split matches how products are actually traded in European markets. This page is volume-only — price "
            "stays on the trading desk — but the shape here is what origination must defend.",
            "Unity Catalog vintages and MLflow reproducibility mean when the board asks why Cal+2 was lifted, you can "
            "point at driver assumptions instead of someone's Excel macro.",
        ),
    ),
    (
        "3 — This page and each widget",
        (
            "Page title and summary: Customer Consumption — Long Term. Position this for curve and origination traders "
            "sizing multi-year hedges, not for the prompt desk squaring today's gate.",
            "Toolbar: Horizon year, scenario, and zone filters shape the story. Pick the high-electrification scenario "
            "to show visible uplift in winter and evening peaks — that is the narrative executives remember.",
            "Status banner: Read the selected scenario headline, winter peak context, and band width at the horizon "
            "year. This frames structural uncertainty before you open charts.",
            "Desk KPI cards: Annual energy P50, winter peak megawatts, P90 uplift versus base, and the scenario label — "
            "give the room the headline numbers risk committees ask for.",
            "Seasonal shape chart: Walk monthly P50 with the P10–P90 ribbon. European books are typically winter-peaking "
            "on heating load. Wider bands further out reflect structural uncertainty, not a broken model.",
            "Scenario comparison chart: Contrast base versus high electrification — evening and winter demand lift. Say "
            "clearly: \"This is why we did not size Cal+2 on last year's meter profile alone.\"",
            "Driver assumptions panel: EV adoption percent, heat-pump percent, efficiency — tie these to the uplift the "
            "charts show. Mention MLflow reproducibility if the room cares about production governance.",
            "Close with conviction: \"The prompt desk inherits what the curve desk sized here — governed long-term "
            "shape flowing into short-term consumption and publication, not a one-off spreadsheet.\"",
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


def _filters_pred(vintage: str, scenario: str, zone: str, year: str) -> str:
    parts = [f"vintage_id = '{ucp.sql_escape(vintage)}'", f"scenario = '{ucp.sql_escape(scenario)}'"]
    if zone and zone != "ALL":
        parts.append(f"zone_code = '{ucp.sql_escape(zone)}'")
    if year and year != "ALL":
        parts.append(f"forecast_year = {int(year)}")
    return " AND ".join(parts)


def _seasonal_shape_chart(rows: list[list[Any]]) -> go.Figure:
    """Grouped bars: season × year with P50 bars and P90 markers."""
    fig = go.Figure()
    if not rows:
        fig.update_layout(template="plotly_white", height=360, margin=ucp.plotly_chart_margins(n_traces=3))
        return fig

    by_year: dict[int, dict[str, tuple[float, float, float]]] = {}
    for row in rows:
        season, year = str(row[0]), int(row[1])
        by_year.setdefault(year, {})[season] = (float(row[2] or 0), float(row[3] or 0), float(row[4] or 0))

    palette = ["#2563eb", "#7c3aed", "#ea580c"]
    years_sorted = sorted(by_year)
    cal_base = years_sorted[0]
    for i, yr in enumerate(years_sorted):
        p50s = [by_year[yr].get(s, (0, 0, 0))[0] for s in _SEASON_ORDER]
        p90s = [by_year[yr].get(s, (0, 0, 0))[2] for s in _SEASON_ORDER]
        color = palette[i % len(palette)]
        label = f"Cal+{yr - cal_base + 1}"
        fig.add_trace(go.Bar(name=label, x=list(_SEASON_ORDER), y=p50s, marker_color=color))
        fig.add_trace(
            go.Scatter(
                x=list(_SEASON_ORDER),
                y=p90s,
                mode="markers",
                marker=dict(symbol="line-ns-open", size=12, color=color),
                name=f"{label} P90",
                showlegend=False,
                hovertemplate="%{x}<br>P90 %{y:.1f} MW<extra></extra>",
            )
        )

    n_traces = len(years_sorted)
    fig.update_layout(
        barmode="group",
        yaxis_title="MW",
        template="plotly_white",
        height=360,
        margin=ucp.plotly_chart_margins(n_traces=n_traces),
        legend=ucp.plotly_legend(n_traces=n_traces),
    )
    return fig


def _scenario_compare_chart(rows: list[list[Any]]) -> go.Figure:
    """BASE vs HIGH_ELECTRIFICATION P50 by season."""
    fig = go.Figure()
    if not rows:
        fig.update_layout(template="plotly_white", height=300, margin=ucp.plotly_chart_margins(n_traces=2))
        return fig

    by_scenario: dict[str, dict[str, float]] = {}
    for row in rows:
        scenario, season, p50 = str(row[0]), str(row[1]), float(row[2] or 0)
        by_scenario.setdefault(scenario, {})[season] = p50

    palette = {"BASE": "#2563eb", "HIGH_ELECTRIFICATION": "#ea580c", "LOW_GROWTH": "#94a3b8"}
    for scenario, seasons in sorted(by_scenario.items()):
        ys = [seasons.get(s, 0) for s in _SEASON_ORDER]
        fig.add_trace(
            go.Scatter(
                x=list(_SEASON_ORDER),
                y=ys,
                name=_SCENARIO_LABELS.get(scenario, scenario),
                mode="lines+markers",
                line=dict(color=palette.get(scenario, "#64748b"), width=2),
            )
        )
    n_traces = len(by_scenario)
    fig.update_layout(
        yaxis_title="P50 MW",
        template="plotly_white",
        height=300,
        margin=ucp.plotly_chart_margins(n_traces=n_traces),
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
                                    html.Span("Curve desk", className="curve-page-badge"),
                                ],
                            ),
                            ucp.presenter_tip_button("vf-lt-presenter-tip-btn"),
                        ],
                    ),
                    uicons.hero_title(_PAGE_TITLE, uicons.VOLUME_FORECAST_NAV_ICONS[_PATH]),
                    html.P(_PAGE_SUMMARY, className="curve-page-summary"),
                ],
            ),
            ucp.presenter_modal(
                _PRESENTER_SECTIONS,
                modal_id="vf-lt-presenter-modal",
                close_id="vf-lt-presenter-close",
                backdrop_id="vf-lt-presenter-backdrop",
                title_id="vf-lt-presenter-modal-title",
                lead=_PRESENTER_LEAD,
            ),
            html.Div(
                className="curve-callout curve-callout-accent",
                children=html.P(
                    "Baseline anchored on the curated meter profile (capability 04). "
                    "Three scenarios under one vintage — compare electrification paths before locking hedges.",
                    className="curve-callout-body",
                ),
            ),
            html.Div(
                className="curve-toolbar st-toolbar",
                children=[
                    html.Div(
                        className="curve-toolbar-field st-toolbar-field-date",
                        children=[
                            html.Label("Vintage", className="curve-toolbar-label"),
                            dcc.Dropdown(
                                id="vf-lt-vintage",
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
                            html.Label("Scenario", className="curve-toolbar-label"),
                            dcc.Dropdown(
                                id="vf-lt-scenario",
                                options=[],
                                value=None,
                                clearable=False,
                                className="toolbar-select st-toolbar-zone",
                                optionHeight=44,
                            ),
                        ],
                    ),
                    html.Div(
                        className="curve-toolbar-field st-toolbar-field-zone",
                        children=[
                            html.Label("Zone", className="curve-toolbar-label"),
                            dcc.Dropdown(
                                id="vf-lt-zone",
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
                            html.Label("Forecast year", className="curve-toolbar-label"),
                            dcc.Dropdown(
                                id="vf-lt-year",
                                options=[{"label": "All years", "value": "ALL"}],
                                value="ALL",
                                clearable=False,
                                className="toolbar-select st-toolbar-zone",
                                optionHeight=44,
                            ),
                        ],
                    ),
                    html.Button("Refresh", id="vf-lt-refresh", type="button", className="curve-refresh-btn"),
                ],
            ),
            dcc.Loading(id="vf-lt-loading", type="default", children=html.Div(id="vf-lt-body")),
        ],
    )


def _body(
    warehouse_id: str,
    vintage: str,
    scenario: str,
    zone: str,
    year: str,
) -> html.Div:
    pred = _filters_pred(vintage, scenario, zone, year)

    # Cal+1 headline year
    cal1_sql = f"""
    SELECT MIN(forecast_year) AS y FROM {ucp.fq("volume_forecast_gold_consumption_lt_shape")}
    WHERE vintage_id = '{ucp.sql_escape(vintage)}' AND scenario = '{ucp.sql_escape(scenario)}'
    """
    cal1_res = ucp.run_uc_sql(warehouse_id, cal1_sql)
    cal1_year = int(cal1_res.rows[0][0]) if cal1_res.ok and cal1_res.rows and cal1_res.rows[0][0] else None

    kpi_pred = (
        pred
        if year != "ALL"
        else (_filters_pred(vintage, scenario, zone, str(cal1_year)) if cal1_year else pred)
    )

    kpi_sql = f"""
    SELECT
        ROUND(AVG(baseload_mw), 1) AS baseload_mw,
        ROUND(AVG(peakload_mw), 1) AS peakload_mw,
        ROUND(AVG(p90_mw), 1) AS p90_mw,
        ROUND(AVG(p50_mw), 1) AS p50_mw,
        MAX(as_of_ts) AS as_of_ts
    FROM {ucp.fq("volume_forecast_gold_consumption_lt_shape")}
    WHERE {kpi_pred}
    """
    kpi_res = ucp.run_uc_sql(warehouse_id, kpi_sql)
    if not kpi_res.ok:
        return _alert(f"Could not load load shape: {kpi_res.error}", kind="error")
    if not kpi_res.rows:
        return _alert("No long-term consumption data for this filter.", kind="warn")

    k = dict(zip(kpi_res.columns, kpi_res.rows[0]))
    baseload = float(k.get("baseload_mw") or 0)
    peakload = float(k.get("peakload_mw") or 0)
    p90 = float(k.get("p90_mw") or 0)
    p50_cal1 = float(k.get("p50_mw") or 0)
    as_of_ts = str(k.get("as_of_ts") or "—")

    uplift_sql = f"""
    SELECT ROUND(AVG(electrification_uplift_mw), 1) AS uplift_mw
    FROM {ucp.fq("volume_forecast_silver_consumption_lt")}
    WHERE {kpi_pred}
    """
    uplift_res = ucp.run_uc_sql(warehouse_id, uplift_sql)
    uplift = float(uplift_res.rows[0][0] or 0) if uplift_res.ok and uplift_res.rows else 0.0

    shape_sql = f"""
    SELECT season, forecast_year,
           ROUND(AVG(p50_mw), 1), ROUND(AVG(p75_mw), 1), ROUND(AVG(p90_mw), 1)
    FROM {ucp.fq("volume_forecast_gold_consumption_lt_shape")}
    WHERE {pred}
    GROUP BY season, forecast_year
    ORDER BY forecast_year, season
    """
    shape_res = ucp.run_uc_sql(warehouse_id, shape_sql)

    # Scenario comparison: BASE + HIGH for selected year (or Cal+1)
    cmp_year = year if year != "ALL" else (str(cal1_year) if cal1_year else "ALL")
    cmp_year_clause = f" AND forecast_year = {int(cmp_year)}" if cmp_year != "ALL" else ""
    cmp_sql = f"""
    SELECT scenario, season, ROUND(AVG(p50_mw), 1)
    FROM {ucp.fq("volume_forecast_silver_consumption_lt")}
    WHERE vintage_id = '{ucp.sql_escape(vintage)}'
      AND scenario IN ('BASE', 'HIGH_ELECTRIFICATION')
      {f"AND zone_code = '{ucp.sql_escape(zone)}'" if zone != 'ALL' else ''}
      {cmp_year_clause}
    GROUP BY scenario, season
    ORDER BY scenario, season
    """
    cmp_res = ucp.run_uc_sql(warehouse_id, cmp_sql)

    driver_sql = f"""
    SELECT forecast_year, zone_code, scenario,
           gdp_growth_pct, ev_penetration_pct, heatpump_penetration_pct, efficiency_trend_pct
    FROM {ucp.fq("volume_forecast_bronze_macro_drivers")}
    WHERE {pred}
    ORDER BY forecast_year, zone_code
    LIMIT 30
    """
    driver_res = ucp.run_uc_sql(warehouse_id, driver_sql)

    scenario_label = _SCENARIO_LABELS.get(scenario, scenario)
    cal_label = f"Cal+1 ({cal1_year})" if cal1_year else "Cal+1"
    year_note = f"year {year}" if year != "ALL" else cal_label

    parts: list[Any] = [
        html.Div(
            className="curve-publication-banner curve-pub-draft",
            children=[
                html.Span(scenario_label, className="curve-pub-badge"),
                html.Span(
                    f"{year_note} P50 ≈ {p50_cal1:.1f} MW · electrification uplift +{uplift:.1f} MW",
                    className="curve-pub-headline",
                ),
                html.Span(f"Vintage {vintage} · as of {as_of_ts}", className="curve-pub-meta"),
            ],
        ),
        html.P(_KPI_LEAD, className="curve-section-lead"),
        html.Div(
            className="curve-outcome-row",
            children=[
                _outcome_card("Baseload", f"{baseload:.1f} MW"),
                _outcome_card("Peakload", f"{peakload:.1f} MW"),
                _outcome_card("P90 layer", f"{p90:.1f} MW"),
                _outcome_card(
                    "Electrification uplift",
                    f"+{uplift:.1f} MW",
                    variant="curve-outcome-warn" if uplift > 20 else "",
                ),
            ],
        ),
        ucp.capability_section(
            "Seasonal shape",
            _WIDGET_SHAPE,
            dcc.Graph(
                figure=_seasonal_shape_chart(shape_res.rows if shape_res.ok else []),
                config={"displayModeBar": False},
            ),
        ),
        ucp.capability_section(
            "Scenario comparison",
            _WIDGET_SCENARIOS,
            dcc.Graph(
                figure=_scenario_compare_chart(cmp_res.rows if cmp_res.ok else []),
                config={"displayModeBar": False},
            ),
        ),
        ucp.capability_section(
            "Driver assumptions",
            _WIDGET_DRIVERS,
            _table(
                ["Year", "Zone", "Scenario", "GDP %", "EV %", "Heat-pump %", "Efficiency %"],
                driver_res.rows if driver_res.ok and driver_res.rows else [],
            )
            if driver_res.ok and driver_res.rows
            else html.P("No driver rows for this filter.", className="curve-muted"),
        ),
        html.P(
            f"Structural forecast vintage {vintage}. Baseline derived from capability 04 meter profile.",
            className="curve-footnote",
        ),
    ]
    return html.Div(className="curve-page-body", children=parts)


@callback(
    Output("vf-lt-vintage", "options"),
    Output("vf-lt-vintage", "value"),
    Output("vf-lt-scenario", "options"),
    Output("vf-lt-scenario", "value"),
    Output("vf-lt-zone", "options"),
    Output("vf-lt-zone", "value"),
    Output("vf-lt-year", "options"),
    Output("vf-lt-year", "value"),
    Input("sql-warehouse-dropdown", "value"),
    Input("vf-lt-refresh", "n_clicks"),
    State("vf-lt-vintage", "value"),
    State("vf-lt-scenario", "value"),
    State("vf-lt-zone", "value"),
    State("vf-lt-year", "value"),
    prevent_initial_call=False,
)
def _load_filters(
    warehouse_id: str | None,
    _n: int | None,
    current_vintage: str | None,
    current_scenario: str | None,
    current_zone: str | None,
    current_year: str | None,
):
    zone_opts = [{"label": "All zones", "value": "ALL"}]
    year_opts = [{"label": "All years", "value": "ALL"}]
    if not warehouse_id:
        return [], None, [], None, zone_opts, ucp.resolve_dropdown_value(current_zone, ["ALL"]), year_opts, ucp.resolve_dropdown_value(current_year, ["ALL"])

    vintages_sql = f"""
    SELECT DISTINCT vintage_id FROM {ucp.fq("volume_forecast_gold_consumption_lt_shape")}
    ORDER BY vintage_id DESC
    """
    scenarios_sql = f"""
    SELECT DISTINCT scenario FROM {ucp.fq("volume_forecast_gold_consumption_lt_shape")}
    ORDER BY scenario
    """
    zones_sql = f"SELECT zone_code, country FROM {ucp.fq('volume_forecast_dim_zones')} ORDER BY zone_code"
    years_sql = f"""
    SELECT DISTINCT forecast_year FROM {ucp.fq("volume_forecast_gold_consumption_lt_shape")}
    ORDER BY forecast_year
    """

    v_res = ucp.run_uc_sql(warehouse_id, vintages_sql)
    s_res = ucp.run_uc_sql(warehouse_id, scenarios_sql)
    z_res = ucp.run_uc_sql(warehouse_id, zones_sql)
    y_res = ucp.run_uc_sql(warehouse_id, years_sql)

    vintages = [str(r[0]) for r in (v_res.rows if v_res.ok else []) if r[0]]
    vintage_opts = [{"label": v, "value": v} for v in vintages]

    scenarios = [str(r[0]) for r in (s_res.rows if s_res.ok else []) if r[0]]
    scenario_opts = [{"label": _SCENARIO_LABELS.get(s, s), "value": s} for s in scenarios]

    if z_res.ok:
        zone_opts += [{"label": f"{r[0]} — {r[1]}", "value": str(r[0])} for r in z_res.rows]

    years = [str(int(r[0])) for r in (y_res.rows if y_res.ok else []) if r[0] is not None]
    if years:
        base = int(years[0])
        year_opts += [{"label": f"Cal+{int(y) - base + 1} ({y})", "value": y} for y in years]

    zone_values = [str(o["value"]) for o in zone_opts]
    year_values = [str(o["value"]) for o in year_opts]
    scenario_values = [str(o["value"]) for o in scenario_opts]

    default_scenario = "BASE" if "BASE" in scenario_values else (scenario_values[0] if scenario_values else None)

    return (
        vintage_opts,
        ucp.resolve_dropdown_value(current_vintage, vintages),
        scenario_opts,
        ucp.resolve_dropdown_value(current_scenario, scenario_values) or default_scenario,
        zone_opts,
        ucp.resolve_dropdown_value(current_zone, zone_values),
        year_opts,
        ucp.resolve_dropdown_value(current_year, year_values),
    )


@callback(
    Output("vf-lt-body", "children"),
    Input("sql-warehouse-dropdown", "value"),
    Input("vf-lt-vintage", "value"),
    Input("vf-lt-scenario", "value"),
    Input("vf-lt-zone", "value"),
    Input("vf-lt-year", "value"),
    Input("vf-lt-refresh", "n_clicks"),
)
def _render_body(
    warehouse_id: str | None,
    vintage: str | None,
    scenario: str | None,
    zone: str | None,
    year: str | None,
    _n: int | None,
):
    if not warehouse_id:
        return ucp.warehouse_prompt()
    if not vintage or not scenario:
        probe = ucp.run_uc_sql(warehouse_id, f"SELECT COUNT(*) FROM {ucp.fq('volume_forecast_gold_consumption_lt_shape')}")
        if probe.ok and probe.rows and int(float(probe.rows[0][0])) > 0:
            return _alert("Filters could not be loaded — choose Refresh.", kind="warn")
        return _alert("No long-term consumption data. Run `energy_trading_demo_data`, then select a connection.", kind="warn")
    return _body(warehouse_id, vintage, scenario, zone or "ALL", year or "ALL")


@callback(
    Output("vf-lt-presenter-modal", "className"),
    Input("vf-lt-presenter-tip-btn", "n_clicks"),
    Input("vf-lt-presenter-close", "n_clicks"),
    Input("vf-lt-presenter-backdrop", "n_clicks"),
    State("vf-lt-presenter-modal", "className"),
    prevent_initial_call=True,
)
def _toggle_presenter(_o, _c, _b, current: str | None):
    base = "curve-presenter-modal"
    return base if current and "curve-presenter-modal-open" in current else f"{base} curve-presenter-modal-open"
