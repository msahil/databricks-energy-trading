"""
Trade capture & pricing — overview (capability 02).

Binds to `02_trade_capture_and_pricing.ipynb` tables; see
`modules/forecasting/features/02-trade-capture-and-pricing.md`.
"""

from __future__ import annotations

import dash
from dash import Input, Output, callback, dcc, html

import m01_common as m1
import m02_common as m2
import shared_ui as su
import uc_sql as uq

dash.register_page(
    __name__,
    path="/trade-capture",
    name="Trade capture overview",
    title="Energy Trading — Trade capture overview",
    order=10,
)

layout = m2.page_shell(
    h1="Trade capture & pricing",
    blurb="""This capability is the **contractual book of record** for OTC-style deals: what traded, **where** (bidding zone), **how** it clears (bilateral vs CCP-style), and which fields look **REMIT-reportable** in a realistic mapping. The overview below is a **morning-style snapshot**—counts, locational mix, clearing split, and a scatter of executions—so front office, middle office, and compliance can **align on the same numbers** before opening the blotter or downstream views.

Use it when you need to **sense-check** synthetic capture data, **brief** a stakeholder on demo scope, or **navigate** to trades, pricing, regulatory, and lifecycle pages in the sidebar.

- **Desk snapshot** — trade count, REMIT-flagged deals, cleared share, and total MW in the demo batch.
- **Locational mix** — MW by bidding zone so you see whether the book is concentrated or spread.
- **Clearing** — bilateral versus cleared-style paths for margin and reporting conversations.
- **Executions** — price versus execution time, coloured by zone, for a quick **pattern** read.
- **Recent deals** — the latest rows from the capture table for spot-checking **IDs and counterparties**.

*Synthetic OTC-style deals only—not live trades or production REMIT submissions. Choose a running warehouse in the header to load data.*
""",
    content_id="trade-capture-content",
    footnote=(
        "Sources: `demo_trades_otc_remit_style` (KPIs, charts, sample grid). "
        "Catalog/schema: README.md / `DEMO_UC_*`."
    ),
)


@callback(
    Output("trade-capture-content", "children"),
    Input("sql-warehouse-dropdown", "value"),
)
def _render_trade_capture(warehouse_id: str | None) -> html.Div:
    if not warehouse_id:
        return m1.select_warehouse_prompt()

    cat, sch = uq.default_catalog_schema()
    t_tr = uq.full_table(cat, sch, "demo_trades_otc_remit_style")

    q_kpi = f"""
        SELECT
            COUNT(*) AS n_trades,
            SUM(volume_mw) AS sum_mw,
            SUM(CASE WHEN remit_reportable_flag THEN 1 ELSE 0 END) AS n_remit,
            SUM(CASE WHEN clearing_mode = 'cleared' THEN 1 ELSE 0 END) AS n_cleared
        FROM {t_tr}
    """
    r_kpi = uq.run_sql(warehouse_id, q_kpi)
    if r_kpi.ok and r_kpi.rows:
        n_t, s_mw, n_rem, n_clr = r_kpi.rows[0][:4]
        try:
            n_trades = int(float(n_t)) if n_t not in ("", None) else 0
        except (TypeError, ValueError):
            n_trades = 0
        try:
            sum_mw = float(s_mw) if s_mw not in ("", None) else 0.0
        except (TypeError, ValueError):
            sum_mw = 0.0
        try:
            n_remit = int(float(n_rem)) if n_rem not in ("", None) else 0
        except (TypeError, ValueError):
            n_remit = 0
        try:
            n_cleared = int(float(n_clr)) if n_clr not in ("", None) else 0
        except (TypeError, ValueError):
            n_cleared = 0
        pct_clr = round(100.0 * n_cleared / n_trades, 1) if n_trades else 0.0
        kpi_trades = str(n_trades)
        kpi_trades_h = "Rows in synthetic OTC capture batch"
        kpi_mw = f"{sum_mw:,.0f} MW"
        kpi_mw_h = "Sum of `volume_mw` across deals (demo units)"
        kpi_remit = str(n_remit)
        kpi_remit_h = "Count with `remit_reportable_flag` true (mapping exercise)"
        kpi_clr = f"{n_cleared} ({pct_clr}%)"
        kpi_clr_h = "Deals with `clearing_mode` = cleared vs bilateral"
    else:
        kpi_trades = "—"
        kpi_trades_h = (r_kpi.error or "?")[:100]
        kpi_mw = "—"
        kpi_mw_h = "—"
        kpi_remit = "—"
        kpi_remit_h = "—"
        kpi_clr = "—"
        kpi_clr_h = "—"

    q_zone = f"""
        SELECT bidding_zone, SUM(volume_mw) AS mw
        FROM {t_tr}
        GROUP BY bidding_zone
        ORDER BY bidding_zone
    """
    r_zone = uq.run_sql(warehouse_id, q_zone)
    if r_zone.ok and r_zone.rows:
        labs = [str(r[0]) for r in r_zone.rows]
        vals = [float(r[1]) if r[1] not in ("", None) else 0.0 for r in r_zone.rows]
        fig_zone = m2.fig_bar_categories(
            labs,
            vals,
            title="Volume by bidding zone (Σ MW)",
            y_title="MW (sum of demo volumes)",
        )
    else:
        fig_zone = m1.empty_fig("Volume by zone", r_zone.error or "No data")

    q_clr = f"""
        SELECT clearing_mode, COUNT(*) AS n
        FROM {t_tr}
        GROUP BY clearing_mode
    """
    r_clr = uq.run_sql(warehouse_id, q_clr)
    if r_clr.ok and r_clr.rows:
        clabs = [str(r[0]) for r in r_clr.rows]
        cvals = [int(float(r[1])) if r[1] not in ("", None) else 0 for r in r_clr.rows]
        fig_clr = m2.fig_pie_counts(clabs, cvals, title="Clearing mode mix (deal count)")
    else:
        fig_clr = m1.empty_fig("Clearing mix", r_clr.error or "No data")

    q_sc = f"""
        SELECT execution_ts_utc, fixed_price_eur_mwh, bidding_zone
        FROM {t_tr}
        ORDER BY execution_ts_utc ASC
    """
    r_sc = uq.run_sql(warehouse_id, q_sc, row_limit=500)
    if r_sc.ok and r_sc.rows:
        xs = [r[0] for r in r_sc.rows]
        ys = [float(r[1]) if r[1] not in ("", None) else None for r in r_sc.rows]
        zs = [str(r[2]) for r in r_sc.rows]
        fig_sc = m2.fig_scatter_exec(
            xs,
            ys,
            zs,
            title="Fixed price vs execution time — by zone",
            y_title="€/MWh",
        )
    else:
        fig_sc = m1.empty_fig("Executions", r_sc.error or "No data")

    q_recent = f"""
        SELECT trade_id, execution_ts_utc, bidding_zone, product_type, volume_mw,
               fixed_price_eur_mwh, clearing_mode, remit_reportable_flag
        FROM {t_tr}
        ORDER BY execution_ts_utc DESC
        LIMIT 15
    """
    r_recent = uq.run_sql(warehouse_id, q_recent, row_limit=50)

    q_prod = f"""
        SELECT product_type, COUNT(*) AS n_deals
        FROM {t_tr}
        GROUP BY product_type
        ORDER BY n_deals DESC
    """
    r_prod = uq.run_sql(warehouse_id, q_prod)

    return html.Div(
        className="space-y-8",
        children=[
            html.Div(
                className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4",
                children=[
                    su.stat_card("Trades in batch", kpi_trades, kpi_trades_h),
                    su.stat_card("Total MW (sum)", kpi_mw, kpi_mw_h),
                    su.stat_card("REMIT-reportable (count)", kpi_remit, kpi_remit_h),
                    su.stat_card("Cleared deals", kpi_clr, kpi_clr_h),
                ],
            ),
            html.Div(
                className="grid gap-6 lg:grid-cols-2",
                children=[
                    html.Div(
                        className="chart-panel p-6",
                        children=[
                            dcc.Graph(figure=fig_zone, config={"displayModeBar": False}, className="-mx-2"),
                            html.P(
                                "Locational concentration — `demo_trades_otc_remit_style.volume_mw` by `bidding_zone`.",
                                className="mt-2 text-xs text-slate-500",
                            ),
                        ],
                    ),
                    html.Div(
                        className="chart-panel p-6",
                        children=[
                            dcc.Graph(figure=fig_clr, config={"displayModeBar": False}, className="-mx-2"),
                            html.P(
                                "Bilateral vs cleared-style capture — `clearing_mode`.",
                                className="mt-2 text-xs text-slate-500",
                            ),
                        ],
                    ),
                ],
            ),
            html.Div(
                className="chart-panel p-6",
                children=[
                    dcc.Graph(figure=fig_sc, config={"displayModeBar": False}, className="-mx-2"),
                    html.P(
                        "Each point is one deal — `execution_ts_utc` vs `fixed_price_eur_mwh`, coloured by zone.",
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
                            html.H2("Product mix (deal counts)", className="mb-3 text-sm font-semibold text-slate-900"),
                            m1.sql_html_table(
                                r_prod,
                                caption="`demo_trades_otc_remit_style` grouped by `product_type`.",
                            ),
                        ],
                    ),
                    html.Div(
                        className="card-elevated overflow-x-auto p-4",
                        children=[
                            html.H2("Latest executions (sample)", className="mb-3 text-sm font-semibold text-slate-900"),
                            m2.sql_table_limited(
                                r_recent,
                                caption="Newest rows — key columns for a quick blotter-style check.",
                                max_rows=15,
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )
