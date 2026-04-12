"""§4.1 — Ingestion: prices & derivatives (demo Delta)."""

from __future__ import annotations

import dash
from dash import Input, Output, callback, dcc, html

import m01_common as m1
import uc_sql as uq

dash.register_page(
    __name__,
    path="/market-data/prices",
    name="M01 prices",
    title="Energy Trading — Prices & power derivatives",
    order=2,
)

layout = m1.page_shell(
    h1="Prices & derivatives",
    blurb="""This page is for **anyone pricing power or explaining spreads**: it shows **hourly cleared power** across Germany–Luxembourg, the Netherlands, and France, and it separates **day-ahead auction** results from **continuous intraday** levels for the same delivery window in DE-LU. That pairing is what desks use to talk about **session risk**, **locational basis**, and whether intraday is bidding up or down against the auction.

The lower section shows how **raw price feeds** would land in a governed store—source, ingestion time, and licence placeholders—so operations and audit can answer “what did we receive, and when?” before data is cleaned and joined downstream.

- **Coupled hubs** — DE-LU, NL, and FR on one hourly canvas so you can compare neighbouring markets without switching contexts.
- **Day-ahead auction** — auction-style hourly results as the main reference for many books.
- **Intraday continuous** — same-zone intraday track for the same delivery to contrast session timing and liquidity.
- **Raw landing** — bronze-style rows showing feed lineage fields your controls team expects to see.
- **Audit trail** — enough metadata to rehearse SLA and compliance questions around vendor and exchange truth.

*Demonstration data only. Technical table and feed identifiers are in the footnote below.*
""",
    content_id="m01-prices-body",
    footnote=(
        "Sources: `demo_prices_spot_hourly` (hourly results), `demo_bronze_prices_spot` (raw landing / lineage)."
    ),
)


@callback(
    Output("m01-prices-body", "children"),
    Input("sql-warehouse-dropdown", "value"),
)
def _render(warehouse_id: str | None) -> html.Div:
    if not warehouse_id:
        return m1.select_warehouse_prompt()

    cat, sch = uq.default_catalog_schema()
    t_p = uq.full_table(cat, sch, "demo_prices_spot_hourly")
    t_b = uq.full_table(cat, sch, "demo_bronze_prices_spot")

    q_zones = f"""
        SELECT delivery_ts, bidding_zone, price_eur_mwh
        FROM {t_p}
        WHERE product_code = 'EPEX_DA_HR' AND bidding_zone IN ('DE-LU', 'NL', 'FR')
        ORDER BY delivery_ts DESC
        LIMIT 504
    """
    rz = uq.run_sql(warehouse_id, q_zones, row_limit=600)
    if rz.ok and rz.rows:
        ser = m1.series_from_long_rows(rz.rows, ts_col=0, name_col=1, val_col=2)
        fig_z = m1.fig_multiline_named(
            ser,
            title="Day-ahead prices — DE-LU, NL, and France",
            y_title="€/MWh",
            x_title="Delivery hour",
        )
    else:
        fig_z = m1.empty_fig("DA by zone", rz.error or "No data")

    q_da_id = f"""
        SELECT delivery_ts, product_code, price_eur_mwh
        FROM {t_p}
        WHERE bidding_zone = 'DE-LU' AND product_code IN ('EPEX_DA_HR', 'EPEX_ID_INDEX_15M')
        ORDER BY delivery_ts DESC
        LIMIT 336
    """
    rj = uq.run_sql(warehouse_id, q_da_id, row_limit=400)
    if rj.ok and rj.rows:
        ser_di = m1.series_from_long_rows(rj.rows, ts_col=0, name_col=1, val_col=2)
        fig_di = m1.fig_multiline_named(
            ser_di,
            title="DE-LU — day-ahead auction vs intraday index (same delivery)",
            y_title="€/MWh",
            x_title="Delivery hour",
            colors=("#0f172a", "#ea580c"),
        )
    else:
        fig_di = m1.empty_fig("DA vs ID", rj.error or "No data")

    q_bronze = f"""
        SELECT ingestion_ts, source_system, dataset_family, bidding_zone_eic, product_code, value, unit, data_license_note
        FROM {t_b}
        ORDER BY ingestion_ts DESC
        LIMIT 32
    """
    rb = uq.run_sql(warehouse_id, q_bronze, row_limit=80)

    q_src = f"""
        SELECT source_system, dataset_family, COUNT(*) AS n_rows
        FROM {t_b}
        GROUP BY source_system, dataset_family
        ORDER BY source_system, dataset_family
    """
    rsrc = uq.run_sql(warehouse_id, q_src, row_limit=50)

    return html.Div(
        className="space-y-8",
        children=[
            html.Div(
                className="grid gap-6 lg:grid-cols-1",
                children=[
                    html.Div(
                        className="chart-panel p-6",
                        children=[
                            dcc.Graph(figure=fig_z, config={"displayModeBar": False}, className="-mx-2"),
                            html.P(
                                "Coupled markets and locational basis (synthetic). `demo_prices_spot_hourly`.",
                                className="mt-2 text-xs text-slate-500",
                            ),
                        ],
                    ),
                    html.Div(
                        className="chart-panel p-6",
                        children=[
                            dcc.Graph(figure=fig_di, config={"displayModeBar": False}, className="-mx-2"),
                            html.P(
                                "Compare auction vs continuous session for the same zone. Products `EPEX_DA_HR`, `EPEX_ID_INDEX_15M` in `demo_prices_spot_hourly`.",
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
                            html.H2("Raw feed landing — lineage sample", className="mb-3 text-sm font-semibold text-slate-900"),
                            m1.sql_html_table(
                                rb,
                                caption="`demo_bronze_prices_spot` — ingestion vs delivery timestamps, source, licence note.",
                            ),
                        ],
                    ),
                    html.Div(
                        className="card-elevated overflow-x-auto p-4",
                        children=[
                            html.H2("Volume by feed source", className="mb-3 text-sm font-semibold text-slate-900"),
                            m1.sql_html_table(
                                rsrc,
                                caption="Row counts by `source_system` and `dataset_family` — `demo_bronze_prices_spot`.",
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )
