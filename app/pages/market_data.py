"""
Market data & visualisation — overview (capability 01).

Widgets are driven by `01_market_data_and_visualisation.ipynb` Delta tables; see
`modules/forecasting/features/01-market-data-and-visualisation.md`.
"""

from __future__ import annotations

import dash
from dash import Input, Output, callback, dcc, html

import m01_common as m1
import shared_ui as su
import uc_sql as uq

dash.register_page(
    __name__,
    path="/",
    name="Market data",
    title="Energy Trading — Market data overview",
    order=1,
    # Sidebar and bookmarks use /market-data — redirect preserves one canonical page at /.
    redirect_from=["/market-data"],
)

layout = m1.page_shell(
    h1="Market data & visualisation",
    blurb="""This is the **landing view** for market data and visualisation: a single screen to orient trading, risk, and analytics before you open the detail routes in the sidebar. It pulls together the same themes the desk watches every morning—where power is pricing, how gas and carbon sit alongside power for margin conversations, and whether German–Luxembourg fundamentals look supportive or stretched.

Use it when you want a **quick pulse** on coupled European hubs, a **TTF-style gas** benchmark, **EU carbon** for thermal plants, **hourly load and renewable proxies** in DE-LU, and the **reference bidding zones** that anchor geography in the demo. The widgets below are sized for overview: high-level time series and KPI-style reads rather than trade-level depth.

- **Power spot** — day-ahead and intraday hourly series so you can compare sessions and zones at a glance.
- **Gas and carbon** — hub gas and allowance levels that frame cross-commodity and hedging discussions.
- **Fundamentals** — load and renewable drivers for DE-LU to connect price moves to underlying demand and supply.
- **Geography** — named bidding zones so locational language stays consistent across the app.
- **Next steps** — when something stands out, jump to Prices, System, Weather, or Visualisation for a focused story.

*Illustrative sample data for demonstration—not live exchange or vendor prices. Choose a running warehouse in the header to load and refresh these views.*
""",
    content_id="market-data-content",
    footnote=(
        "Data: `demo_prices_spot_hourly`, `demo_gas_hub_ttf_style`, `demo_reference_bidding_zones`, `demo_fundamentals_de_lu` "
        "(catalog/schema: README.md / DEMO_UC_*)."
    ),
)


@callback(
    Output("market-data-content", "children"),
    Input("sql-warehouse-dropdown", "value"),
)
def _render_market_data(warehouse_id: str | None) -> html.Div:
    if not warehouse_id:
        return m1.select_warehouse_prompt()

    cat, sch = uq.default_catalog_schema()
    t_prices = uq.full_table(cat, sch, "demo_prices_spot_hourly")
    t_ttf = uq.full_table(cat, sch, "demo_gas_hub_ttf_style")
    t_zones = uq.full_table(cat, sch, "demo_reference_bidding_zones")
    t_fund = uq.full_table(cat, sch, "demo_fundamentals_de_lu")

    q_da = f"""
        SELECT delivery_ts, price_eur_mwh
        FROM {t_prices}
        WHERE bidding_zone = 'DE-LU' AND product_code = 'EPEX_DA_HR'
        ORDER BY delivery_ts DESC
        LIMIT 1
    """
    r_da = uq.run_sql(warehouse_id, q_da)
    if r_da.ok and r_da.rows:
        px, ts = r_da.rows[0][1], r_da.rows[0][0]
        kpi_da_val = f"€{px}/MWh" if px not in ("", None) else "—"
        kpi_da_hint = f"Day-ahead auction product · latest hour {ts}"
    else:
        kpi_da_val = "—"
        kpi_da_hint = (r_da.error or "No row")[:120]

    q_id = f"""
        SELECT delivery_ts, price_eur_mwh
        FROM {t_prices}
        WHERE bidding_zone = 'DE-LU' AND product_code = 'EPEX_ID_INDEX_15M'
        ORDER BY delivery_ts DESC
        LIMIT 1
    """
    r_id = uq.run_sql(warehouse_id, q_id)
    if r_id.ok and r_id.rows:
        px, ts = r_id.rows[0][1], r_id.rows[0][0]
        kpi_id_val = f"€{px}/MWh" if px not in ("", None) else "—"
        kpi_id_hint = f"Intraday index (15m-style) · {ts}"
    else:
        kpi_id_val = "—"
        kpi_id_hint = (r_id.error or "No row")[:120]

    q_ttf = f"""
        SELECT gas_day_date, price, unit
        FROM {t_ttf}
        ORDER BY gas_day_date DESC
        LIMIT 1
    """
    r_ttf = uq.run_sql(warehouse_id, q_ttf)
    if r_ttf.ok and r_ttf.rows:
        gd, pr, un = r_ttf.rows[0][:3]
        kpi_ttf_val = f"{pr} {un or ''}".strip()
        kpi_ttf_hint = f"Dutch TTF benchmark · gas day {gd}"
    else:
        kpi_ttf_val = "—"
        kpi_ttf_hint = (r_ttf.error or "No row")[:120]

    q_nz = f"SELECT COUNT(*) AS n FROM {t_zones}"
    r_nz = uq.run_sql(warehouse_id, q_nz)
    if r_nz.ok and r_nz.rows:
        nz = r_nz.rows[0][0]
        kpi_nz_val = str(int(float(nz))) if nz not in ("", None) else "—"
        kpi_nz_hint = "Zones in reference master (`demo_reference_bidding_zones`)"
    else:
        kpi_nz_val = "—"
        kpi_nz_hint = (r_nz.error or "?")[:80]

    q_three = f"""
        SELECT delivery_ts, bidding_zone, price_eur_mwh
        FROM {t_prices}
        WHERE product_code = 'EPEX_DA_HR' AND bidding_zone IN ('DE-LU', 'NL', 'FR')
        ORDER BY delivery_ts DESC
        LIMIT 504
    """
    r3 = uq.run_sql(warehouse_id, q_three, row_limit=600)
    if r3.ok and r3.rows:
        ser = m1.series_from_long_rows(r3.rows, ts_col=0, name_col=1, val_col=2)
        fig_zones = m1.fig_multiline_named(
            ser,
            title="Day-ahead prices — Germany–Luxembourg, Netherlands, France",
            y_title="€/MWh",
            x_title="Delivery hour",
        )
    else:
        fig_zones = m1.empty_fig("DA prices by zone", r3.error or "No data")

    q_ser = f"""
        SELECT delivery_ts, price_eur_mwh
        FROM {t_prices}
        WHERE bidding_zone = 'DE-LU' AND product_code = 'EPEX_DA_HR'
        ORDER BY delivery_ts DESC
        LIMIT 168
    """
    r_ser = uq.run_sql(warehouse_id, q_ser, row_limit=500)
    if r_ser.ok and r_ser.rows:
        fig_p = m1.fig_prices(r_ser.rows)
        fig_p.update_layout(
            title=dict(text="Germany–Luxembourg — day-ahead (last week of hours)", font=dict(size=14), x=0.02, xanchor="left"),
            margin=dict(t=64),
        )
        fig_p.update_traces(name="Day-ahead")
        fig_p.update_xaxes(title="Delivery hour")
        fig_p.update_yaxes(title="€/MWh")
    else:
        fig_p = m1.empty_fig("DE-LU DA (168h)", r_ser.error or "No data")

    q_fun = f"""
        SELECT ts, load_mw, solar_mw_est, wind_ms
        FROM {t_fund}
        WHERE zone = 'DE-LU'
        ORDER BY ts DESC
        LIMIT 168
    """
    r_fun = uq.run_sql(warehouse_id, q_fun, row_limit=500)
    if r_fun.ok and r_fun.rows:
        fig_f = m1.fig_fundamentals(r_fun.rows)
        fig_f.update_layout(
            title=dict(text="Load, solar estimate, and wind speed — DE-LU zone", font=dict(size=14), x=0.02, xanchor="left"),
            margin=dict(t=72),
        )
    else:
        fig_f = m1.empty_fig("DE-LU fundamentals", r_fun.error or "No data")

    q_prod = f"""
        SELECT bidding_zone, product_code, COUNT(*) AS n_hours
        FROM {t_prices}
        GROUP BY bidding_zone, product_code
        ORDER BY bidding_zone, product_code
    """
    r_prod = uq.run_sql(warehouse_id, q_prod, row_limit=50)

    q_z = f"""
        SELECT zone_code, name, country, eic_bidding_zone
        FROM {t_zones}
        ORDER BY zone_code
        LIMIT 12
    """
    r_z = uq.run_sql(warehouse_id, q_z, row_limit=100)

    return html.Div(
        className="space-y-8",
        children=[
            html.Div(
                className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4",
                children=[
                    su.stat_card("DE-LU day-ahead (latest hour)", kpi_da_val, kpi_da_hint),
                    su.stat_card("DE-LU intraday index (latest)", kpi_id_val, kpi_id_hint),
                    su.stat_card("TTF gas benchmark (latest day)", kpi_ttf_val, kpi_ttf_hint),
                    su.stat_card("Reference zones in catalog", kpi_nz_val, kpi_nz_hint),
                ],
            ),
            html.Div(
                className="chart-panel p-6",
                children=[
                    dcc.Graph(figure=fig_zones, config={"displayModeBar": False}, className="-mx-2"),
                    html.P(
                        "Locational view of coupled markets (synthetic). Source: `demo_prices_spot_hourly`, day-ahead product.",
                        className="mt-2 text-xs text-slate-500",
                    ),
                ],
            ),
            html.Div(
                className="grid gap-6 lg:grid-cols-2",
                children=[
                    html.Div(
                        className="chart-panel p-6",
                        children=[
                            dcc.Graph(figure=fig_p, config={"displayModeBar": False}, className="-mx-2"),
                            html.P(
                                "Single-zone focus for trend reading. Source: `demo_prices_spot_hourly`.",
                                className="mt-2 text-xs text-slate-500",
                            ),
                        ],
                    ),
                    html.Div(
                        className="chart-panel p-6",
                        children=[
                            dcc.Graph(figure=fig_f, config={"displayModeBar": False}, className="-mx-2"),
                            html.P(
                                "Fundamentals for short-term operations context (synthetic). Source: `demo_fundamentals_de_lu` — MW left, wind m/s right.",
                                className="mt-2 text-xs text-slate-500",
                            ),
                        ],
                    ),
                ],
            ),
            html.Div(
                className="grid gap-6 lg:grid-cols-2",
                children=[
                    html.Div(
                        className="card-elevated overflow-x-auto p-4",
                        children=[
                            html.H2("Coverage by zone and product", className="mb-3 text-sm font-semibold text-slate-900"),
                            m1.sql_html_table(
                                r_prod,
                                caption="Row counts — `demo_prices_spot_hourly` by `bidding_zone` × `product_code`.",
                            ),
                        ],
                    ),
                    html.Div(
                        className="card-elevated overflow-x-auto p-4",
                        children=[
                            html.H2("Bidding zones — reference master (sample)", className="mb-3 text-sm font-semibold text-slate-900"),
                            m1.sql_html_table(
                                r_z,
                                caption="EIC-style keys for geography — `demo_reference_bidding_zones`, sample rows.",
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )
