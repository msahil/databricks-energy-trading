"""Capability 02 — Contracts & downstream exports (catalogue-style demo)."""

from __future__ import annotations

import dash
from dash import Input, Output, callback, html

import m01_common as m1
import m02_common as m2
import uc_sql as uq

dash.register_page(
    __name__,
    path="/trade-capture/lifecycle",
    name="M02 lifecycle",
    title="Energy Trading — Contracts & downstream",
    order=14,
)

layout = m2.page_shell(
    h1="Contracts & downstream",
    blurb="""Captured trades are not the end of the story: **consumer systems** subscribe to **contracts** with versioned terms, and **analytics** pipelines **export** handoffs to forecast tables and risk engines. This page shows the **catalogue-style** registries that accompany the trade batch—who **consumes** data, **contract status**, and **export** jobs with **table references** and **schema versions**—so operations can rehearse **downstream lineage** from deal to model.

Use it when you explain **onboarding** a new internal consumer, **reviewing** a contract in flight, or **tracing** which **Delta** table an export targeted in the demo world.

- **Consumer contracts** — internal consumer id, **version**, **status**, and **notes** on delivery format.
- **Exports** — batch-style **export_id**, **consumer**, **forecast scope**, **status**, and **target table** string.
- **Versions** — `schema_version` on exports to mirror **API evolution** conversations.
- **Operations** — read-only mirror of how **handoffs** would be monitored in production.
- **Linkage** — complements **Trades** (economic truth) with **who pulled what** metadata.

*Synthetic registry rows—not production SLAs or ticket queues. Warehouse loads tables from footnote.*
""",
    content_id="m02-lifecycle-body",
    footnote=(
        "Sources: `demo_consumer_contracts` — `consumer_id`, `contract_version`, `status`, `notes`; "
        "`demo_downstream_exports` — export metadata including `table_ref`, `schema_version`."
    ),
)


@callback(
    Output("m02-lifecycle-body", "children"),
    Input("sql-warehouse-dropdown", "value"),
)
def _render(warehouse_id: str | None) -> html.Div:
    if not warehouse_id:
        return m1.select_warehouse_prompt()

    cat, sch = uq.default_catalog_schema()
    t_c = uq.full_table(cat, sch, "demo_consumer_contracts")
    t_e = uq.full_table(cat, sch, "demo_downstream_exports")

    q_c = f"SELECT * FROM {t_c} ORDER BY consumer_id"
    r_c = uq.run_sql(warehouse_id, q_c, row_limit=100)

    q_e = f"SELECT * FROM {t_e} ORDER BY exported_at DESC"
    r_e = uq.run_sql(warehouse_id, q_e, row_limit=100)

    return html.Div(
        className="space-y-8",
        children=[
            html.Div(
                className="grid gap-6 lg:grid-cols-2",
                children=[
                    html.Div(
                        className="card-elevated overflow-x-auto p-4",
                        children=[
                            html.H2("Consumer contracts", className="mb-3 text-sm font-semibold text-slate-900"),
                            m1.sql_html_table(
                                r_c,
                                caption="Internal consumers and contract versions — `demo_consumer_contracts`.",
                            ),
                        ],
                    ),
                    html.Div(
                        className="card-elevated overflow-x-auto p-4",
                        children=[
                            html.H2("Downstream exports", className="mb-3 text-sm font-semibold text-slate-900"),
                            m1.sql_html_table(
                                r_e,
                                caption="Handoff jobs toward forecast and risk tables — `demo_downstream_exports`.",
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )
