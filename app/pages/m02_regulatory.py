"""Capability 02 — Regulatory & clearing view (REMIT-shaped demo)."""

from __future__ import annotations

import dash
from dash import Input, Output, callback, dcc, html

import m01_common as m1
import m02_common as m2
import shared_ui as su
import uc_sql as uq

dash.register_page(
    __name__,
    path="/trade-capture/regulatory",
    name="M02 regulatory",
    title="Energy Trading — Regulatory & clearing",
    order=13,
)

layout = m2.page_shell(
    h1="Regulatory & clearing",
    blurb="""Compliance and reporting teams need **counterparty identifiers**, **clearing** status, and **REMIT**-oriented flags **alongside** the economic fields. This view aggregates the **demo capture** so you can rehearse **how many** deals are flagged reportable, how **LEIs** distribute across counterparties, and how **bilateral vs cleared** splits look—without connecting to a real **RRM** or **trade repository**.

Use it in **UAT-style** conversations: validate that your **field mapping** lines up with ACER-style expectations **before** you plug in XML exports.

- **REMIT flag** — share of deals marked `remit_reportable_flag` true vs false in the synthetic batch.
- **Clearing** — bilateral versus cleared counts for EMIR-style margin and reporting narratives.
- **Counterparties** — trades per **simulated LEI** so you see concentration at entity level.
- **Product coverage** — deal counts by `product_type` for scope discussions.
- **Audit** — read-only; production would append **UTI**, **action type**, and **versioning** per refit rules.

*Synthetic identifiers and flags—not submissions to regulators. Source table in footnote.*
""",
    content_id="m02-regulatory-body",
    footnote="Source: `demo_trades_otc_remit_style` — `remit_reportable_flag`, `clearing_mode`, `counterparty_lei_simulated`, `product_type`.",
)


@callback(
    Output("m02-regulatory-body", "children"),
    Input("sql-warehouse-dropdown", "value"),
)
def _render(warehouse_id: str | None) -> html.Div:
    if not warehouse_id:
        return m1.select_warehouse_prompt()

    cat, sch = uq.default_catalog_schema()
    t_tr = uq.full_table(cat, sch, "demo_trades_otc_remit_style")

    q_rem = f"""
        SELECT
            CASE WHEN remit_reportable_flag THEN 'reportable' ELSE 'not_flagged' END AS remit_bucket,
            COUNT(*) AS n
        FROM {t_tr}
        GROUP BY remit_bucket
    """
    r_rem = uq.run_sql(warehouse_id, q_rem)
    if r_rem.ok and r_rem.rows:
        lr = [str(r[0]) for r in r_rem.rows]
        vr = [int(float(r[1])) if r[1] not in ("", None) else 0 for r in r_rem.rows]
        fig_rem = m2.fig_pie_counts(lr, vr, title="REMIT-reportable flag (deal count)")
    else:
        fig_rem = m1.empty_fig("REMIT mix", r_rem.error or "No data")

    q_clr = f"""
        SELECT clearing_mode, COUNT(*) AS n
        FROM {t_tr}
        GROUP BY clearing_mode
    """
    r_clr = uq.run_sql(warehouse_id, q_clr)
    if r_clr.ok and r_clr.rows:
        lc = [str(r[0]) for r in r_clr.rows]
        vc = [int(float(r[1])) if r[1] not in ("", None) else 0 for r in r_clr.rows]
        fig_clr = m2.fig_pie_counts(lc, vc, title="Clearing mode (deal count)")
    else:
        fig_clr = m1.empty_fig("Clearing", r_clr.error or "No data")

    q_lei = f"""
        SELECT counterparty_lei_simulated, COUNT(*) AS n_trades
        FROM {t_tr}
        GROUP BY counterparty_lei_simulated
        ORDER BY n_trades DESC
    """
    r_lei = uq.run_sql(warehouse_id, q_lei, row_limit=50)

    q_pt = f"""
        SELECT product_type, COUNT(*) AS n
        FROM {t_tr}
        GROUP BY product_type
        ORDER BY n DESC
    """
    r_pt = uq.run_sql(warehouse_id, q_pt)

    q_kpi = f"SELECT COUNT(DISTINCT counterparty_lei_simulated) AS n_lei, COUNT(*) AS n_tr FROM {t_tr}"
    r_k = uq.run_sql(warehouse_id, q_kpi)
    if r_k.ok and r_k.rows:
        n_lei, n_tr = r_k.rows[0][:2]
        try:
            nl = int(float(n_lei)) if n_lei not in ("", None) else 0
        except (TypeError, ValueError):
            nl = 0
        try:
            nt = int(float(n_tr)) if n_tr not in ("", None) else 0
        except (TypeError, ValueError):
            nt = 0
        s1 = str(nl)
        s1h = "Distinct simulated LEIs in batch"
        s2 = str(nt)
        s2h = "Total deals for denominator checks"
    else:
        s1 = "—"
        s1h = (r_k.error or "?")[:80]
        s2 = "—"
        s2h = "—"

    return html.Div(
        className="space-y-8",
        children=[
            html.Div(
                className="grid gap-4 sm:grid-cols-2",
                children=[
                    su.stat_card("Distinct LEIs (simulated)", s1, s1h),
                    su.stat_card("Total deals", s2, s2h),
                ],
            ),
            html.Div(
                className="grid gap-6 lg:grid-cols-2",
                children=[
                    html.Div(
                        className="chart-panel p-6",
                        children=[
                            dcc.Graph(figure=fig_rem, config={"displayModeBar": False}, className="-mx-2"),
                            html.P(
                                "`remit_reportable_flag` — mapping exercise only.",
                                className="mt-2 text-xs text-slate-500",
                            ),
                        ],
                    ),
                    html.Div(
                        className="chart-panel p-6",
                        children=[
                            dcc.Graph(figure=fig_clr, config={"displayModeBar": False}, className="-mx-2"),
                            html.P(
                                "`clearing_mode` — bilateral vs cleared-style paths.",
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
                            html.H2("Trades per counterparty LEI", className="mb-3 text-sm font-semibold text-slate-900"),
                            m1.sql_html_table(
                                r_lei,
                                caption="`counterparty_lei_simulated` — concentration at legal-entity level (demo).",
                            ),
                        ],
                    ),
                    html.Div(
                        className="card-elevated overflow-x-auto p-4",
                        children=[
                            html.H2("Product type coverage", className="mb-3 text-sm font-semibold text-slate-900"),
                            m1.sql_html_table(
                                r_pt,
                                caption="Deal counts by `product_type` for regulatory scope review.",
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )
