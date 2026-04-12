"""Capability 04 — Backtesting."""

from __future__ import annotations

import dash
from dash import Input, Output, callback, dcc, html

import m01_common as m1
import m02_common as m2
import m04_common as m4
import shared_ui as su
import uc_sql as uq

dash.register_page(
    __name__,
    path="/strategy/backtest",
    name="M04 backtest",
    title="Energy Trading — Strategy backtests",
    order=32,
)

layout = m4.page_shell(
    h1="Backtesting",
    blurb="""Backtests in this accelerator are **governed artefacts**: each row ties a **strategy** to a **run id** with **simulated PnL**, **Sharpe**, and **max drawdown** so model risk can ask **reproducibility** questions. The demo does not include **full cost ladders** or **slippage** calibration—those belong in §4.2 implementation—but the **shape** of the table matches what a **committee pack** would attach.

Use this page to **compare** strategies on **risk-adjusted** metrics and to **scan** the raw grid when you explain **why** a run is or is not **promotable**.

- **PnL bar** — **net** simulated EUR by strategy for the packaged run.
- **Risk metrics** — **Sharpe** and **drawdown** as headline **tail** indicators.
- **Currency** — `currency` column keeps **FX** conversations explicit in multi-currency books.
- **Conduct** — spec reminds that **wash trades** and **fictitious liquidity** are out of scope; demo numbers are **honestly synthetic**.
- **Replay** — `backtest_run_id` is the **join key** to deeper artefacts offline.

*Simulated metrics—not a certified backtest report.*
""",
    content_id="m04-backtest-body",
    footnote=(
        "Source: `demo_backtest_summary` — `strategy_id`, `backtest_run_id`, `net_pnl_eur_sim`, "
        "`sharpe_ratio_sim`, `max_drawdown_eur_sim`, `currency`."
    ),
)


@callback(
    Output("m04-backtest-body", "children"),
    Input("sql-warehouse-dropdown", "value"),
)
def _render(warehouse_id: str | None) -> html.Div:
    if not warehouse_id:
        return m1.select_warehouse_prompt()

    cat, sch = uq.default_catalog_schema()
    t = uq.full_table(cat, sch, "demo_backtest_summary")

    q = f"SELECT * FROM {t} ORDER BY strategy_id"
    r = uq.run_sql(warehouse_id, q, row_limit=50)

    q_bar = f"SELECT strategy_id, net_pnl_eur_sim FROM {t}"
    r_b = uq.run_sql(warehouse_id, q_bar, row_limit=20)
    if r_b.ok and r_b.rows:
        lbs = [str(row[0]) for row in r_b.rows]
        vals = [float(row[1]) if row[1] not in ("", None) else 0.0 for row in r_b.rows]
        fig = m2.fig_bar_categories(
            lbs,
            vals,
            title="Net PnL (simulated) by strategy",
            y_title="€",
            color="#ff3621",
        )
    else:
        fig = m1.empty_fig("Net PnL", r_b.error or "No data")

    q_kpi = f"""
        SELECT AVG(sharpe_ratio_sim) AS s, AVG(max_drawdown_eur_sim) AS d
        FROM {t}
    """
    r_k = uq.run_sql(warehouse_id, q_kpi)
    if r_k.ok and r_k.rows:
        s, d = r_k.rows[0][:2]
        try:
            sv = float(s) if s not in ("", None) else None
        except (TypeError, ValueError):
            sv = None
        try:
            dv = float(d) if d not in ("", None) else None
        except (TypeError, ValueError):
            dv = None
        k1 = f"{sv:.2f}" if sv is not None else "—"
        k1h = "Mean `sharpe_ratio_sim` across rows"
        k2 = f"€{dv:,.0f}" if dv is not None else "—"
        k2h = "Mean `max_drawdown_eur_sim` (more negative = deeper drawdown)"
    else:
        k1 = "—"
        k1h = (r_k.error or "?")[:80]
        k2 = "—"
        k2h = "—"

    return html.Div(
        className="space-y-8",
        children=[
            html.Div(
                className="grid gap-4 sm:grid-cols-2",
                children=[
                    su.stat_card("Mean Sharpe (sim)", k1, k1h),
                    su.stat_card("Mean max drawdown (sim)", k2, k2h),
                ],
            ),
            html.Div(
                className="chart-panel p-6",
                children=[
                    dcc.Graph(figure=fig, config={"displayModeBar": False}, className="-mx-2"),
                    html.P(
                        "Single run id per strategy in the demo batch — see table.",
                        className="mt-2 text-xs text-slate-500",
                    ),
                ],
            ),
            html.Div(
                className="card-elevated overflow-x-auto p-4",
                children=[
                    html.H2("Backtest summary grid", className="mb-3 text-sm font-semibold text-slate-900"),
                    m1.sql_html_table(
                        r,
                        caption="Full `demo_backtest_summary` output.",
                    ),
                ],
            ),
        ],
    )
