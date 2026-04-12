"""Capability 04 — Portfolio & asset optimisation (scenario framing)."""

from __future__ import annotations

import dash
from dash import Input, Output, callback, dcc, html

import m01_common as m1
import m02_common as m2
import m04_common as m4
import uc_sql as uq

dash.register_page(
    __name__,
    path="/strategy/optimisation",
    name="M04 optimisation",
    title="Energy Trading — Optimisation & scenarios",
    order=33,
)

layout = m4.page_shell(
    h1="Portfolio & asset optimisation",
    blurb="""Optimisation in energy trading sits on **constraints**: **contracts**, **grid**, **storage SOC**, and **risk** limits. The demo does not run a **solver** in the app; instead it exposes **scenario definitions** and **monthly KPI** aggregates that desks use to **frame** objectives—**CVaR** caps, **margin** targets, and **stress** paths—before **quant** pushes a model to **batch**.

Pair **scenarios** with **dashboard KPIs** to narrate how **mark sensitivity** and **ensemble spread** behave across **months** in the synthetic book.

- **Scenarios** — **central**, **dunkelflaute**, **negative prices**, **import constraints**, **gas-led spark**, **cold** — plain-language **effects**.
- **KPI trends** — **MAE**, **mark sensitivity**, **consumption rate**, **ensemble spread** by month for DE-LU.
- **Horizons** — spec covers **intraday** through **seasonal**; demo KPIs are **monthly** aggregates.
- **Storage** — scenario table includes a **storage_optimisation** scope row in the catalogue (see Spec page).
- **Honesty** — no **optimal dispatch** vector is shown—only **inputs** to the conversation.

*Scenario labels and KPIs are synthetic—not optimised portfolio outputs.*
""",
    content_id="m04-optimisation-body",
    footnote=(
        "Sources: `demo_scenario_definitions`, `demo_dashboard_kpis` — `month`, `kpi`, `zone`, `value`, `unit`."
    ),
)


@callback(
    Output("m04-optimisation-body", "children"),
    Input("sql-warehouse-dropdown", "value"),
)
def _render(warehouse_id: str | None) -> html.Div:
    if not warehouse_id:
        return m1.select_warehouse_prompt()

    cat, sch = uq.default_catalog_schema()
    t_sc = uq.full_table(cat, sch, "demo_scenario_definitions")
    t_k = uq.full_table(cat, sch, "demo_dashboard_kpis")

    r_sc = uq.run_sql(warehouse_id, f"SELECT * FROM {t_sc} ORDER BY scenario_id", row_limit=50)

    q_k = f"""
        SELECT month, kpi, value, unit
        FROM {t_k}
        WHERE zone = 'DE-LU'
        ORDER BY month, kpi
    """
    r_k = uq.run_sql(warehouse_id, q_k, row_limit=200)

    q_mae = f"""
        SELECT month, value
        FROM {t_k}
        WHERE zone = 'DE-LU' AND kpi = 'forecast_mae_da'
        ORDER BY month
    """
    r_mae = uq.run_sql(warehouse_id, q_mae, row_limit=20)
    if r_mae.ok and r_mae.rows:
        lbs = [str(row[0]) for row in r_mae.rows]
        vals = [float(row[1]) if row[1] not in ("", None) else 0.0 for row in r_mae.rows]
        fig_mae = m2.fig_bar_categories(
            lbs,
            vals,
            title="Monthly forecast MAE — DE-LU (dashboard KPI)",
            y_title="€/MWh",
            color="#2563eb",
        )
    else:
        fig_mae = m1.empty_fig("MAE by month", r_mae.error or "No data")

    q_sens = f"""
        SELECT month, value
        FROM {t_k}
        WHERE zone = 'DE-LU' AND kpi = 'mark_sensitivity_eur'
        ORDER BY month
    """
    r_sens = uq.run_sql(warehouse_id, q_sens, row_limit=20)
    if r_sens.ok and r_sens.rows:
        lbs2 = [str(row[0]) for row in r_sens.rows]
        vals2 = [float(row[1]) if row[1] not in ("", None) else 0.0 for row in r_sens.rows]
        fig_sens = m2.fig_bar_categories(
            lbs2,
            vals2,
            title="Mark sensitivity — EUR per 1 €/MWh DA move",
            y_title="EUR",
            color="#059669",
        )
    else:
        fig_sens = m1.empty_fig("Mark sensitivity", r_sens.error or "No data")

    return html.Div(
        className="space-y-8",
        children=[
            html.Div(
                className="card-elevated overflow-x-auto p-4",
                children=[
                    html.H2("Stress & scenario definitions", className="mb-3 text-sm font-semibold text-slate-900"),
                    m1.sql_html_table(
                        r_sc,
                        caption="`demo_scenario_definitions` — labels for optimisation and risk workshops.",
                    ),
                ],
            ),
            html.Div(
                className="grid gap-6 lg:grid-cols-2",
                children=[
                    html.Div(
                        className="chart-panel p-6",
                        children=[
                            dcc.Graph(figure=fig_mae, config={"displayModeBar": False}, className="-mx-2"),
                            html.P(
                                "`forecast_mae_da` — `demo_dashboard_kpis`.",
                                className="mt-2 text-xs text-slate-500",
                            ),
                        ],
                    ),
                    html.Div(
                        className="chart-panel p-6",
                        children=[
                            dcc.Graph(figure=fig_sens, config={"displayModeBar": False}, className="-mx-2"),
                            html.P(
                                "`mark_sensitivity_eur` — book sensitivity narrative (synthetic).",
                                className="mt-2 text-xs text-slate-500",
                            ),
                        ],
                    ),
                ],
            ),
            html.Div(
                className="card-elevated overflow-x-auto p-4",
                children=[
                    html.H2("Dashboard KPIs (full slice)", className="mb-3 text-sm font-semibold text-slate-900"),
                    m1.sql_html_table(
                        r_k,
                        caption="All KPI rows for DE-LU — includes ensemble spread and consumption rate.",
                    ),
                ],
            ),
        ],
    )
