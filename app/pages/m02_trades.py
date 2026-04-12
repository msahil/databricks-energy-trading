"""Capability 02 — Trade blotter (demo OTC / REMIT-shaped)."""

from __future__ import annotations

import dash
from dash import Input, Output, callback, dcc, html

import m01_common as m1
import m02_common as m2
import uc_sql as uq

dash.register_page(
    __name__,
    path="/trade-capture/trades",
    name="M02 trades",
    title="Energy Trading — Trades blotter",
    order=11,
)

layout = m2.page_shell(
    h1="Trades blotter",
    blurb="""The **blotter** is the operational list of captured deals: identifiers, **execution time**, **zone**, **product**, **volume**, **price**, **counterparty LEI** placeholders, and **clearing** path. Middle office and confirmations use this shape to **match** against broker statements and to prepare **REMIT** and **EMIR** handoffs—here it is **synthetic**, but the column names mirror what a reporting mapping exercise would consume.

Open this page when you need to **scroll the full batch**, **copy** identifiers into a ticket, or **verify** that ingestion preserved REMIT-oriented flags end to end.

- **Row-level detail** — every deal in the demo table with all capture columns.
- **Newest first** — sorted by execution time so the latest synthetic trades appear at the top.
- **Traceability** — `source_note` reminds you the feed is a **demo** generator, not production.
- **Handoff** — pairs with **Regulatory** and **Lifecycle** when you explain lineage beyond the trade itself.
- **Scope** — OTC-style **FWD_SWAP_HR** and related demo products only; no exchange order book.

*Demonstration data. Full table name and catalog in the footnote.*
""",
    content_id="m02-trades-body",
    footnote="Source: `demo_trades_otc_remit_style` — all columns, `ORDER BY execution_ts_utc DESC`, row limit 800.",
)


@callback(
    Output("m02-trades-body", "children"),
    Input("sql-warehouse-dropdown", "value"),
)
def _render(warehouse_id: str | None) -> html.Div:
    if not warehouse_id:
        return m1.select_warehouse_prompt()

    cat, sch = uq.default_catalog_schema()
    t_tr = uq.full_table(cat, sch, "demo_trades_otc_remit_style")

    q = f"""
        SELECT
            trade_id,
            execution_ts_utc,
            bidding_zone,
            product_type,
            volume_mw,
            price_type,
            fixed_price_eur_mwh,
            counterparty_lei_simulated,
            clearing_mode,
            remit_reportable_flag,
            source_note
        FROM {t_tr}
        ORDER BY execution_ts_utc DESC
    """
    r = uq.run_sql(warehouse_id, q, row_limit=800)

    return html.Div(
        className="space-y-6",
        children=[
            html.Div(
                className="card-elevated overflow-x-auto p-4",
                children=[
                    html.H2("Captured deals", className="mb-3 text-sm font-semibold text-slate-900"),
                    m1.sql_html_table(
                        r,
                        caption="Synthetic OTC capture — REMIT-oriented fields (`remit_reportable_flag`, `counterparty_lei_simulated`, `clearing_mode`).",
                    ),
                ],
            ),
        ],
    )
