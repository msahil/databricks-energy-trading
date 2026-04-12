"""§4.4 — Data quality & governance (demo Delta)."""

from __future__ import annotations

import dash
from dash import Input, Output, callback, html

import m01_common as m1
import shared_ui as su
import uc_sql as uq

dash.register_page(
    __name__,
    path="/market-data/governance",
    name="M01 governance",
    title="Energy Trading — Data quality & lineage",
    order=5,
)

layout = m1.page_shell(
    h1="Data quality & governance",
    blurb="""Governance and control teams need to answer **lineage** questions before they trust a price: **which feed**, **when it landed**, **under which licence**, and **how much volume** each source contributed. This page is aimed at **audit, data owners, and second-line** review: it shows **bronze-style** raw price rows with the fields you would expect in a governed ingestion layer, so you can rehearse **data-quality conversations** without touching production tools.

Pair it with **Prices** when you need to prove that **downstream** hourly and daily tables trace back to identifiable **vendor or exchange** families in the demo.

- **Ingestion freshness** — first and last arrival times so you can talk about SLA and delay.
- **Source mix** — how much volume sits under each source and dataset family.
- **Row-level sample** — a slice of raw rows with **source, licence placeholder, and timestamps** for audit drill-down.
- **Separation of concerns** — reinforces the line between **raw feed truth** and **modelled or curated** layers.
- **Production gap** — in real life you would add **quality flags**, **promotion rules**, and **restatement** handling—called out here so expectations stay honest.

*Synthetic demo. Production typically adds automated quality scoring, alerts, and promotion workflows on top of this pattern.*
""",
    content_id="m01-governance-body",
    footnote="Primary source: `demo_bronze_prices_spot` (raw landing / lineage).",
)


@callback(
    Output("m01-governance-body", "children"),
    Input("sql-warehouse-dropdown", "value"),
)
def _render(warehouse_id: str | None) -> html.Div:
    if not warehouse_id:
        return m1.select_warehouse_prompt()

    cat, sch = uq.default_catalog_schema()
    t_b = uq.full_table(cat, sch, "demo_bronze_prices_spot")

    q = f"""
        SELECT ingestion_ts, source_system, dataset_family, delivery_start_ts, bidding_zone_eic,
               product_code, value, unit, data_license_note
        FROM {t_b}
        ORDER BY ingestion_ts DESC
        LIMIT 36
    """
    r = uq.run_sql(warehouse_id, q, row_limit=200)

    q_src = f"""
        SELECT source_system, COUNT(*) AS n_rows
        FROM {t_b}
        GROUP BY source_system
        ORDER BY source_system
    """
    r_src = uq.run_sql(warehouse_id, q_src, row_limit=50)

    q_fam = f"""
        SELECT dataset_family, COUNT(*) AS n_rows
        FROM {t_b}
        GROUP BY dataset_family
        ORDER BY dataset_family
    """
    r_fam = uq.run_sql(warehouse_id, q_fam, row_limit=50)

    q_range = f"""
        SELECT
            MIN(ingestion_ts) AS first_ingestion,
            MAX(ingestion_ts) AS last_ingestion,
            COUNT(DISTINCT delivery_start_ts) AS distinct_delivery_hours
        FROM {t_b}
    """
    r_range = uq.run_sql(warehouse_id, q_range, row_limit=10)

    kpi_first = kpi_last = kpi_h = "—"
    if r_range.ok and r_range.rows and len(r_range.rows[0]) >= 3:
        kpi_first, kpi_last, kpi_h = (str(r_range.rows[0][i]) for i in range(3))

    return html.Div(
        className="space-y-8",
        children=[
            html.Div(
                className="grid gap-4 sm:grid-cols-3",
                children=[
                    su.stat_card("First bronze ingestion", kpi_first, "Earliest `ingestion_ts` in demo range"),
                    su.stat_card("Latest bronze ingestion", kpi_last, "Most recent `ingestion_ts`"),
                    su.stat_card("Delivery hours covered", kpi_h, "Distinct `delivery_start_ts` values"),
                ],
            ),
            html.Ul(
                className="list-inside list-disc space-y-2 text-sm text-slate-600",
                children=[
                    html.Li("Bronze is append-only in this demo; production may version restated series."),
                    html.Li("Source and dataset family identify the feed; pair with code version in real lineage."),
                    html.Li("Licence placeholder marks synthetic data — live feeds would carry subscription / redistribution text."),
                ],
            ),
            html.Div(
                className="grid gap-6 lg:grid-cols-2",
                children=[
                    html.Div(
                        className="card-elevated overflow-x-auto p-4",
                        children=[
                            html.H2("Volume by feed source", className="mb-3 text-sm font-semibold text-slate-900"),
                            m1.sql_html_table(r_src, caption="Rows per `source_system` — `demo_bronze_prices_spot`."),
                        ],
                    ),
                    html.Div(
                        className="card-elevated overflow-x-auto p-4",
                        children=[
                            html.H2("Volume by dataset family", className="mb-3 text-sm font-semibold text-slate-900"),
                            m1.sql_html_table(r_fam, caption="Exchange results vs intraday index families — `demo_bronze_prices_spot`."),
                        ],
                    ),
                ],
            ),
            html.Div(
                className="card-elevated overflow-x-auto p-4",
                children=[
                    html.H2("Bronze landing — sample rows", className="mb-3 text-sm font-semibold text-slate-900"),
                    m1.sql_html_table(r, caption="Latest rows — `demo_bronze_prices_spot`. Ingestion vs delivery, source, licence."),
                ],
            ),
        ],
    )
