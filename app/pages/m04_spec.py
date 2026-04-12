"""Capability 04 — Assisted strategy specification."""

from __future__ import annotations

import dash
from dash import Input, Output, callback, html

import m01_common as m1
import m04_common as m4
import uc_sql as uq

dash.register_page(
    __name__,
    path="/strategy/spec",
    name="M04 spec",
    title="Energy Trading — Strategy specification",
    order=31,
)

layout = m4.page_shell(
    h1="Assisted strategy specification",
    blurb="""Production strategies need **named universes**, **deployment mode**, and **plain-language** documentation beside the code or no-code graph id. This page surfaces the **strategy definition** rows, the **forecast scope catalogue** (which forecast feeds which use case), and **user personas** so UAT stories stay grounded—**paper**, **shadow**, and **pilot** are explicit, not buzzwords.

Use it when you **template** a new idea: which **products** and **zones** apply, who **consumes** the forecast scopes, and which **role** signs off in the demo org chart.

- **Definitions** — `strategy_id`, **status**, **deployment_mode**, and **created** date for governance.
- **Forecast scopes** — maps **scope_id** to **forecast_type**, **use_case**, and **product**.
- **Personas** — desk vs B2B vs risk roles for **acceptance** narratives.
- **Guardrails** — spec §4.1 requires **lookahead** checks; the UI **reminds** via footnotes, not hidden logic.
- **Exports** — backtest and risk **attachments** would link from here in a full workflow.

*Demo registry rows—not an approved strategy catalogue.*
""",
    content_id="m04-spec-body",
    footnote=(
        "Sources: `demo_strategy_definitions`, `demo_forecast_scope_catalog`, `demo_user_personas`."
    ),
)


@callback(
    Output("m04-spec-body", "children"),
    Input("sql-warehouse-dropdown", "value"),
)
def _render(warehouse_id: str | None) -> html.Div:
    if not warehouse_id:
        return m1.select_warehouse_prompt()

    cat, sch = uq.default_catalog_schema()
    t_s = uq.full_table(cat, sch, "demo_strategy_definitions")
    t_f = uq.full_table(cat, sch, "demo_forecast_scope_catalog")
    t_p = uq.full_table(cat, sch, "demo_user_personas")

    r_s = uq.run_sql(warehouse_id, f"SELECT * FROM {t_s} ORDER BY strategy_id", row_limit=50)
    r_f = uq.run_sql(warehouse_id, f"SELECT * FROM {t_f} ORDER BY scope_id", row_limit=50)
    r_p = uq.run_sql(warehouse_id, f"SELECT * FROM {t_p} ORDER BY persona_id", row_limit=50)

    return html.Div(
        className="space-y-8",
        children=[
            html.Div(
                className="card-elevated overflow-x-auto p-4",
                children=[
                    html.H2("Strategy definitions", className="mb-3 text-sm font-semibold text-slate-900"),
                    m1.sql_html_table(
                        r_s,
                        caption="Parameterised strategy metadata — `demo_strategy_definitions`.",
                    ),
                ],
            ),
            html.Div(
                className="grid gap-6 lg:grid-cols-2",
                children=[
                    html.Div(
                        className="card-elevated overflow-x-auto p-4",
                        children=[
                            html.H2("Forecast scope catalogue", className="mb-3 text-sm font-semibold text-slate-900"),
                            m1.sql_html_table(
                                r_f,
                                caption="Links forecast outputs to use cases — `demo_forecast_scope_catalog`.",
                            ),
                        ],
                    ),
                    html.Div(
                        className="card-elevated overflow-x-auto p-4",
                        children=[
                            html.H2("User personas (demo)", className="mb-3 text-sm font-semibold text-slate-900"),
                            m1.sql_html_table(
                                r_p,
                                caption="`demo_user_personas` — `external_customer` flags B2B-style consumers.",
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )
