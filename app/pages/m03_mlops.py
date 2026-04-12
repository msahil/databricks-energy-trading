"""Capability 03 — MLOps & governance (drift, regimes, carbon context)."""

from __future__ import annotations

import dash
from dash import Input, Output, callback, dcc, html

import m01_common as m1
import m03_common as m3
import uc_sql as uq

dash.register_page(
    __name__,
    path="/forecasting/mlops",
    name="M03 MLOps",
    title="Energy Trading — Forecast MLOps",
    order=24,
)

layout = m3.page_shell(
    h1="MLOps & governance",
    blurb="""Production forecasting needs **more than accuracy**: **drift** on inputs, **labels** for **structural breaks**, and **carbon/gas** context when **thermal** assets sit in the stack. This route combines **PSI-style** drift from the demo table, **regime metadata** for storytelling, and the **daily carbon/spark** strip so governance conversations can reference **the same artefacts** as the model card—**registry ids**, **schema versions**, and **monitoring** thresholds would plug in on top in real life.

Use it when you rehearse **promotion** reviews: is drift **elevated** on **price** features versus **load**, and do **regime tags** explain **known** market phases in the demo window.

- **Input drift** — **PSI** by **feature group** over `as_of_date` for the stacked model id.
- **Regimes** — **driver / effect** labels by month tag for **documentation**.
- **Carbon / spark** — **EUA**, **TTF**, and **clean spark proxy** for **margin** context adjacent to power forecasts.
- **Scope** — no live **MLflow** UI here; table rows **stand in** for monitoring exports.
- **Alerts** — production would **threshold** PSI and open tickets—shown as **narrative** only.

*Demo monitoring metrics—not production alerts or SHAP runs.*
""",
    content_id="m03-mlops-body",
    footnote=(
        "Sources: `demo_drift_metrics` — `psi`, `feature_group`, `as_of_date`; "
        "`demo_regime_labels`; `demo_carbon_spark_daily` — `eua_eur_t`, `ttf_eur_mwh`, `clean_spark_proxy`."
    ),
)


@callback(
    Output("m03-mlops-body", "children"),
    Input("sql-warehouse-dropdown", "value"),
)
def _render(warehouse_id: str | None) -> html.Div:
    if not warehouse_id:
        return m1.select_warehouse_prompt()

    cat, sch = uq.default_catalog_schema()
    t_d = uq.full_table(cat, sch, "demo_drift_metrics")
    t_r = uq.full_table(cat, sch, "demo_regime_labels")
    t_c = uq.full_table(cat, sch, "demo_carbon_spark_daily")

    q_d = f"SELECT as_of_date, model_id, feature_group, zone, psi FROM {t_d} ORDER BY as_of_date ASC"
    r_d = uq.run_sql(warehouse_id, q_d, row_limit=500)
    if r_d.ok and r_d.rows:
        fig_d = m3.fig_drift_psi(r_d.rows)
    else:
        fig_d = m1.empty_fig("Drift (PSI)", r_d.error or "No data")

    q_r = f"SELECT * FROM {t_r} ORDER BY month_tag, regime_id"
    r_r = uq.run_sql(warehouse_id, q_r, row_limit=50)

    q_c = f"""
        SELECT ts, zone, eua_eur_t, goo_eur_mwh, ttf_eur_mwh, clean_spark_proxy
        FROM {t_c}
        ORDER BY ts DESC
        LIMIT 90
    """
    r_c = uq.run_sql(warehouse_id, q_c, row_limit=120)
    if r_c.ok and r_c.rows:
        fig_c = m3.fig_carbon_spark(r_c.rows)
    else:
        fig_c = m1.empty_fig("Carbon / spark", r_c.error or "No data")

    q_d_table = f"SELECT * FROM {t_d} ORDER BY as_of_date DESC LIMIT 40"
    r_dt = uq.run_sql(warehouse_id, q_d_table, row_limit=50)

    return html.Div(
        className="space-y-8",
        children=[
            html.Div(
                className="chart-panel p-6",
                children=[
                    dcc.Graph(figure=fig_d, config={"displayModeBar": False}, className="-mx-2"),
                    html.P(
                        "`psi` — population stability-style index on feature groups (synthetic).",
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
                            html.H2("Drift detail (latest rows)", className="mb-3 text-sm font-semibold text-slate-900"),
                            m1.sql_html_table(
                                r_dt,
                                caption="`demo_drift_metrics` — weekly as-of stamps in the generator.",
                            ),
                        ],
                    ),
                    html.Div(
                        className="card-elevated overflow-x-auto p-4",
                        children=[
                            html.H2("Regime labels", className="mb-3 text-sm font-semibold text-slate-900"),
                            m1.sql_html_table(
                                r_r,
                                caption="`demo_regime_labels` — metadata for structural narratives.",
                            ),
                        ],
                    ),
                ],
            ),
            html.Div(
                className="chart-panel p-6",
                children=[
                    dcc.Graph(figure=fig_c, config={"displayModeBar": False}, className="-mx-2"),
                    html.P(
                        "GOO column available in table; chart highlights EUA, TTF, clean spark.",
                        className="mt-2 text-xs text-slate-500",
                    ),
                ],
            ),
        ],
    )
