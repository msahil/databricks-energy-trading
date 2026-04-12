"""Capability 02 — Pricing & exposure snapshot from captured trades."""

from __future__ import annotations

import dash
from dash import Input, Output, callback, dcc, html

import m01_common as m1
import m02_common as m2
import shared_ui as su
import uc_sql as uq

dash.register_page(
    __name__,
    path="/trade-capture/pricing",
    name="M02 pricing",
    title="Energy Trading — Pricing & exposure",
    order=12,
)

layout = m2.page_shell(
    h1="Pricing & exposure",
    blurb="""Risk and finance need a **repeatable mark story** on top of captured economics: for this demo, we approximate **exposure** using **volume** and **fixed price** from each deal—**not** a full valuation engine. The charts show **notional-style proxies** (MW × €/MWh) by **zone** and **product**, plus **average fixed price** by zone, so you can rehearse how **desk-level** views would tie back to **curve-based** marks in production.

Use this page to **compare** locational and product concentration, and to **sanity-check** that simple aggregates match what you see on the **overview** scatter.

- **Notional proxy** — Σ (volume × fixed price) by zone; interpret as a **rough scale** indicator in €·MW-style demo units.
- **Product split** — same proxy summed by `product_type` for structural risk conversations.
- **Average price** — mean fixed €/MWh by zone for a quick **level** comparison.
- **KPIs** — batch-wide average price and largest single-zone proxy share.
- **Limits** — no options vol, no curve uplift—those belong in a full **§4.3** implementation.

*No live marks or vendor curves—aggregates from `demo_trades_otc_remit_style` only.*
""",
    content_id="m02-pricing-body",
    footnote=(
        "Aggregates: `demo_trades_otc_remit_style` — `volume_mw`, `fixed_price_eur_mwh`, `bidding_zone`, `product_type`."
    ),
)


@callback(
    Output("m02-pricing-body", "children"),
    Input("sql-warehouse-dropdown", "value"),
)
def _render(warehouse_id: str | None) -> html.Div:
    if not warehouse_id:
        return m1.select_warehouse_prompt()

    cat, sch = uq.default_catalog_schema()
    t_tr = uq.full_table(cat, sch, "demo_trades_otc_remit_style")

    q_kpi = f"""
        SELECT
            AVG(fixed_price_eur_mwh) AS avg_px,
            SUM(volume_mw * fixed_price_eur_mwh) AS sum_notional_proxy
        FROM {t_tr}
    """
    r_kpi = uq.run_sql(warehouse_id, q_kpi)
    if r_kpi.ok and r_kpi.rows:
        avg_px, sum_n = r_kpi.rows[0][:2]
        try:
            ap = float(avg_px) if avg_px not in ("", None) else 0.0
        except (TypeError, ValueError):
            ap = 0.0
        try:
            sn = float(sum_n) if sum_n not in ("", None) else 0.0
        except (TypeError, ValueError):
            sn = 0.0
        k1 = f"€{ap:.2f}/MWh"
        k1h = "Mean `fixed_price_eur_mwh` across deals"
        k2 = f"{sn:,.0f}"
        k2h = "Σ (volume_mw × fixed_price_eur_mwh) — notional proxy (demo)"
    else:
        k1 = "—"
        k1h = (r_kpi.error or "?")[:80]
        k2 = "—"
        k2h = "—"

    q_zone = f"""
        SELECT
            bidding_zone,
            SUM(volume_mw * fixed_price_eur_mwh) AS notional_proxy
        FROM {t_tr}
        GROUP BY bidding_zone
        ORDER BY bidding_zone
    """
    r_zone = uq.run_sql(warehouse_id, q_zone)
    if r_zone.ok and r_zone.rows:
        lz = [str(r[0]) for r in r_zone.rows]
        vz = [float(r[1]) if r[1] not in ("", None) else 0.0 for r in r_zone.rows]
        fig_z = m2.fig_bar_categories(
            lz,
            vz,
            title="Notional proxy by bidding zone — Σ (MW × €/MWh)",
            y_title="Proxy (sum of products)",
            color="#2563eb",
        )
    else:
        fig_z = m1.empty_fig("Zone notionals", r_zone.error or "No data")

    q_pt = f"""
        SELECT
            product_type,
            SUM(volume_mw * fixed_price_eur_mwh) AS notional_proxy
        FROM {t_tr}
        GROUP BY product_type
        ORDER BY product_type
    """
    r_pt = uq.run_sql(warehouse_id, q_pt)
    if r_pt.ok and r_pt.rows:
        lp = [str(r[0]) for r in r_pt.rows]
        vp = [float(r[1]) if r[1] not in ("", None) else 0.0 for r in r_pt.rows]
        fig_p = m2.fig_bar_categories(
            lp,
            vp,
            title="Notional proxy by product type",
            y_title="Proxy (sum of products)",
            color="#059669",
        )
    else:
        fig_p = m1.empty_fig("Product notionals", r_pt.error or "No data")

    q_avg = f"""
        SELECT bidding_zone, AVG(fixed_price_eur_mwh) AS avg_fix
        FROM {t_tr}
        GROUP BY bidding_zone
        ORDER BY bidding_zone
    """
    r_avg = uq.run_sql(warehouse_id, q_avg)
    if r_avg.ok and r_avg.rows:
        la = [str(r[0]) for r in r_avg.rows]
        va = [float(r[1]) if r[1] not in ("", None) else 0.0 for r in r_avg.rows]
        fig_a = m2.fig_bar_categories(
            la,
            va,
            title="Average fixed price by zone",
            y_title="€/MWh",
            color="#ff3621",
        )
    else:
        fig_a = m1.empty_fig("Avg price by zone", r_avg.error or "No data")

    return html.Div(
        className="space-y-8",
        children=[
            html.Div(
                className="grid gap-4 sm:grid-cols-2",
                children=[
                    su.stat_card("Mean fixed price (batch)", k1, k1h),
                    su.stat_card("Batch notional proxy (sum)", k2, k2h),
                ],
            ),
            html.Div(
                className="grid gap-6 lg:grid-cols-2",
                children=[
                    html.Div(
                        className="chart-panel p-6",
                        children=[
                            dcc.Graph(figure=fig_z, config={"displayModeBar": False}, className="-mx-2"),
                            html.P(
                                "Exposure scale indicator — not a mark from external curves.",
                                className="mt-2 text-xs text-slate-500",
                            ),
                        ],
                    ),
                    html.Div(
                        className="chart-panel p-6",
                        children=[
                            dcc.Graph(figure=fig_p, config={"displayModeBar": False}, className="-mx-2"),
                            html.P(
                                "Structural mix by `product_type` using the same proxy definition.",
                                className="mt-2 text-xs text-slate-500",
                            ),
                        ],
                    ),
                ],
            ),
            html.Div(
                className="chart-panel p-6",
                children=[
                    dcc.Graph(figure=fig_a, config={"displayModeBar": False}, className="-mx-2"),
                    html.P(
                        "Simple average of `fixed_price_eur_mwh` per zone — compare against market levels on Market data pages.",
                        className="mt-2 text-xs text-slate-500",
                    ),
                ],
            ),
        ],
    )
