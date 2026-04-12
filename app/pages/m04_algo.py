"""Capability 04 — Algorithmic & automated trading (controls narrative)."""

from __future__ import annotations

import dash
from dash import Input, Output, callback, dcc, html

import m01_common as m1
import m02_common as m2
import m04_common as m4
import uc_sql as uq

dash.register_page(
    __name__,
    path="/strategy/algo",
    name="M04 algo",
    title="Energy Trading — Algo trading controls",
    order=34,
)

layout = m4.page_shell(
    h1="Algorithmic & automated trading",
    blurb="""Automated and **semi-automated** routes need **deployment mode**, **pre-trade** style rules, and a **clear** line to **kill** and **reconcile** paths in the full spec. Here we **surface** strategy **deployment** (paper / shadow / pilot) and **alert rules** that stand in for **limit** and **surveillance** thresholds—**MiFID** inventory and **OMS** hooks would sit **outside** this demo UI.

Use this page to **brief** compliance on **how** strategies are **classified** and **which** market signals would **raise** automated **warnings** before an order is sent.

- **Deployment mix** — count of strategies by **deployment_mode** from definitions.
- **Rule inventory** — **threshold** rules on **DA**, **spread**, **MAE**, **drift PSI**, **imbalance** index.
- **Severity path** — events are on the **Monitoring** route; rules here are the **static** config.
- **Kill switch** — narrative only; production would **wire** to **OMS** and **risk** services.
- **Modes** — **shadow** vs **paper** vs **pilot** vocabulary matches §4.4 **promotion** language.

*No live order flow or venue sessions—configuration views only.*
""",
    content_id="m04-algo-body",
    footnote=(
        "Sources: `demo_strategy_definitions` (`deployment_mode`), `demo_alert_rules`."
    ),
)


@callback(
    Output("m04-algo-body", "children"),
    Input("sql-warehouse-dropdown", "value"),
)
def _render(warehouse_id: str | None) -> html.Div:
    if not warehouse_id:
        return m1.select_warehouse_prompt()

    cat, sch = uq.default_catalog_schema()
    t_st = uq.full_table(cat, sch, "demo_strategy_definitions")
    t_rg = uq.full_table(cat, sch, "demo_alert_rules")

    q_dep = f"""
        SELECT deployment_mode, COUNT(*) AS n
        FROM {t_st}
        GROUP BY deployment_mode
    """
    r_d = uq.run_sql(warehouse_id, q_dep, row_limit=20)
    if r_d.ok and r_d.rows:
        lbs = [str(r[0]) for r in r_d.rows]
        vals = [int(float(r[1])) if r[1] not in ("", None) else 0 for r in r_d.rows]
        fig = m2.fig_pie_counts(lbs, vals, title="Strategies by deployment mode")
    else:
        fig = m1.empty_fig("Deployment mix", r_d.error or "No data")

    r_full = uq.run_sql(warehouse_id, f"SELECT * FROM {t_st} ORDER BY strategy_id", row_limit=50)
    r_rules = uq.run_sql(warehouse_id, f"SELECT * FROM {t_rg} ORDER BY rule_id", row_limit=50)

    return html.Div(
        className="space-y-8",
        children=[
            html.Div(
                className="chart-panel p-6",
                children=[
                    dcc.Graph(figure=fig, config={"displayModeBar": False}, className="-mx-2"),
                    html.P(
                        "`demo_strategy_definitions.deployment_mode` — paper / shadow / pilot in the synthetic set.",
                        className="mt-2 text-xs text-slate-500",
                    ),
                ],
            ),
            html.Div(
                className="grid gap-6 lg:grid-cols-2",
                children=[
                    html.Div(
                        className="card-elevated overflow-x-auto p-4",
                        children=[
                            html.H2("Strategy definitions", className="mb-3 text-sm font-semibold text-slate-900"),
                            m1.sql_html_table(
                                r_full,
                                caption="Full definitions — promotion gates use **status** + **deployment_mode**.",
                            ),
                        ],
                    ),
                    html.Div(
                        className="card-elevated overflow-x-auto p-4",
                        children=[
                            html.H2("Alert rules (pre-trade / monitoring)", className="mb-3 text-sm font-semibold text-slate-900"),
                            m1.sql_html_table(
                                r_rules,
                                caption="`demo_alert_rules` — `series`, `comparator`, `threshold`, `unit`.",
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )
