"""Capability 04 — Monitoring & incident."""

from __future__ import annotations

import dash
from dash import Input, Output, callback, html

import m01_common as m1
import m04_common as m4
import uc_sql as uq

dash.register_page(
    __name__,
    path="/strategy/monitoring",
    name="M04 monitoring",
    title="Energy Trading — Monitoring & incidents",
    order=35,
)

layout = m4.page_shell(
    h1="Monitoring & incident",
    blurb="""Operations and **on-call** need **alerts**, **KPIs**, and **market context** in one place: **who** was paged, **what** rule fired, and **what else** was happening on the **grid** or **exchange**. This page lists **synthetic alert events**, the full **rule** catalogue, **monthly dashboard KPIs**, and a **TSO / market event** log so incident playbooks can be **walked through** without production **tickets**.

Pair **HIGH** severities with **TSO** events to rehearse **correlation** analysis; production would add **latency histograms** and **reconciliation** breaks per §4.5.

- **Events** — time-ordered **severity** with **message** text for runbooks.
- **Rules** — join key **rule_id** back to thresholds on the **Algo** page.
- **KPIs** — same **dashboard** table as **Optimisation** for **operational** review.
- **Context** — **TSO** and **market** announcements as **timeline** context.
- **Reconciliation** — not wired here; footnotes point to **broker** vs **exchange** artefacts in real life.

*Synthetic events—not live paging or production monitoring.*
""",
    content_id="m04-monitoring-body",
    footnote=(
        "Sources: `demo_alert_events`, `demo_alert_rules`, `demo_dashboard_kpis`, `demo_tso_market_events`."
    ),
)


@callback(
    Output("m04-monitoring-body", "children"),
    Input("sql-warehouse-dropdown", "value"),
)
def _render(warehouse_id: str | None) -> html.Div:
    if not warehouse_id:
        return m1.select_warehouse_prompt()

    cat, sch = uq.default_catalog_schema()
    t_e = uq.full_table(cat, sch, "demo_alert_events")
    t_r = uq.full_table(cat, sch, "demo_alert_rules")
    t_k = uq.full_table(cat, sch, "demo_dashboard_kpis")
    t_t = uq.full_table(cat, sch, "demo_tso_market_events")

    r_e = uq.run_sql(
        warehouse_id,
        f"SELECT * FROM {t_e} ORDER BY event_ts DESC",
        row_limit=50,
    )
    r_r = uq.run_sql(warehouse_id, f"SELECT * FROM {t_r} ORDER BY rule_id", row_limit=50)
    r_k = uq.run_sql(
        warehouse_id,
        f"SELECT * FROM {t_k} WHERE zone = 'DE-LU' ORDER BY month DESC, kpi",
        row_limit=100,
    )
    r_t = uq.run_sql(
        warehouse_id,
        f"SELECT * FROM {t_t} ORDER BY event_ts DESC",
        row_limit=50,
    )

    return html.Div(
        className="space-y-8",
        children=[
            html.Div(
                className="card-elevated overflow-x-auto p-4",
                children=[
                    html.H2("Alert events (newest first)", className="mb-3 text-sm font-semibold text-slate-900"),
                    m1.sql_html_table(
                        r_e,
                        caption="`demo_alert_events` — synthetic severities for incident drills.",
                    ),
                ],
            ),
            html.Div(
                className="grid gap-6 lg:grid-cols-2",
                children=[
                    html.Div(
                        className="card-elevated overflow-x-auto p-4",
                        children=[
                            html.H2("Alert rules", className="mb-3 text-sm font-semibold text-slate-900"),
                            m1.sql_html_table(
                                r_r,
                                caption="`demo_alert_rules` — threshold configuration.",
                            ),
                        ],
                    ),
                    html.Div(
                        className="card-elevated overflow-x-auto p-4",
                        children=[
                            html.H2("Dashboard KPIs (DE-LU)", className="mb-3 text-sm font-semibold text-slate-900"),
                            m1.sql_html_table(
                                r_k,
                                caption="`demo_dashboard_kpis` — monthly operational aggregates.",
                            ),
                        ],
                    ),
                ],
            ),
            html.Div(
                className="card-elevated overflow-x-auto p-4",
                children=[
                    html.H2("TSO & market events", className="mb-3 text-sm font-semibold text-slate-900"),
                    m1.sql_html_table(
                        r_t,
                        caption="`demo_tso_market_events` — operational context for post-mortems.",
                    ),
                ],
            ),
        ],
    )
