"""Capability 03 — Price & spread forecasting (probabilistic demo)."""

from __future__ import annotations

import dash
from dash import Input, Output, callback, dcc, html

import m01_common as m1
import m03_common as m3
import uc_sql as uq

dash.register_page(
    __name__,
    path="/forecasting/prices",
    name="M03 prices",
    title="Energy Trading — Price forecasts",
    order=22,
)

layout = m3.page_shell(
    h1="Price & spread forecasting",
    blurb="""Power desks rarely work from a **single number**: they need a **mid** for the auction or session, a **band** when risk books scenarios, and a **stress** read when **imbalance** risk spikes. The demo price table carries **mid**, **q10/q90**, and an **imbalance risk index** per product row so you can practise **probabilistic** storytelling aligned to **gate timings** in the parent spec.

Pair the **fan chart** (day-ahead) with **multi-product mids** to see how **intraday** and **imbalance-style** rows sit against the **DA** path—still **synthetic**, but shaped like a **multi-product** forecast pack.

- **DA fan** — mid with **quantile band** for `EPEX_DA_HR` in DE-LU.
- **Product comparison** — mids for DA, intraday-style, and imbalance rows on one timeline.
- **Imbalance risk** — `imbalance_risk_index` as a second view for short-term **system** stress.
- **Cut-offs** — narrative only here; timestamps are **UTC-style** demo stamps.
- **Vendor parity** — production would add **purchased** forecasts side-by-side per §4.3.

*Demo quantiles—not exchange clearing prices or official auction results.*
""",
    content_id="m03-prices-body",
    footnote=(
        "Source: `demo_forecasts_market_prices` — `mid_eur_mwh`, `q10_eur_mwh`, `q90_eur_mwh`, `imbalance_risk_index`, `product`."
    ),
)


@callback(
    Output("m03-prices-body", "children"),
    Input("sql-warehouse-dropdown", "value"),
)
def _render(warehouse_id: str | None) -> html.Div:
    if not warehouse_id:
        return m1.select_warehouse_prompt()

    cat, sch = uq.default_catalog_schema()
    t = uq.full_table(cat, sch, "demo_forecasts_market_prices")

    q_fan = f"""
        SELECT ts, mid_eur_mwh, q10_eur_mwh, q90_eur_mwh
        FROM {t}
        WHERE zone = 'DE-LU' AND product = 'EPEX_DA_HR'
        ORDER BY ts DESC
        LIMIT 336
    """
    r_fan = uq.run_sql(warehouse_id, q_fan, row_limit=400)
    if r_fan.ok and r_fan.rows:
        fig_fan = m3.fig_price_fan_da(r_fan.rows)
    else:
        fig_fan = m1.empty_fig("DA fan", r_fan.error or "No data")

    q_long = f"""
        SELECT ts, product, mid_eur_mwh
        FROM {t}
        WHERE zone = 'DE-LU'
        ORDER BY ts DESC
        LIMIT 504
    """
    r_long = uq.run_sql(warehouse_id, q_long, row_limit=600)
    if r_long.ok and r_long.rows:
        ser = m1.series_from_long_rows(r_long.rows, ts_col=0, name_col=1, val_col=2)
        fig_mid = m1.fig_multiline_named(
            ser,
            title="Forecast mid by product — DE-LU",
            y_title="€/MWh",
            x_title="Time",
        )
    else:
        fig_mid = m1.empty_fig("Mids by product", r_long.error or "No data")

    q_imb = f"""
        SELECT ts, product, imbalance_risk_index
        FROM {t}
        WHERE zone = 'DE-LU'
        ORDER BY ts DESC
        LIMIT 504
    """
    r_imb = uq.run_sql(warehouse_id, q_imb, row_limit=600)
    if r_imb.ok and r_imb.rows:
        ser_i = m1.series_from_long_rows(r_imb.rows, ts_col=0, name_col=1, val_col=2)
        fig_imb = m1.fig_multiline_named(
            ser_i,
            title="Imbalance risk index — by product",
            y_title="Index (unitless demo)",
            x_title="Time",
        )
    else:
        fig_imb = m1.empty_fig("Imbalance risk", r_imb.error or "No data")

    return html.Div(
        className="space-y-8",
        children=[
            html.Div(
                className="chart-panel p-6",
                children=[
                    dcc.Graph(figure=fig_fan, config={"displayModeBar": False}, className="-mx-2"),
                    html.P(
                        "Fan chart uses `q10_eur_mwh` / `q90_eur_mwh` as bounds.",
                        className="mt-2 text-xs text-slate-500",
                    ),
                ],
            ),
            html.Div(
                className="chart-panel p-6",
                children=[
                    dcc.Graph(figure=fig_mid, config={"displayModeBar": False}, className="-mx-2"),
                    html.P(
                        "`EPEX_DA_HR`, `EPEX_ID_XBID_15m`, `imbalance_de` — synthetic product keys.",
                        className="mt-2 text-xs text-slate-500",
                    ),
                ],
            ),
            html.Div(
                className="chart-panel p-6",
                children=[
                    dcc.Graph(figure=fig_imb, config={"displayModeBar": False}, className="-mx-2"),
                    html.P(
                        "`imbalance_risk_index` — higher implies heavier tail risk in the demo definition.",
                        className="mt-2 text-xs text-slate-500",
                    ),
                ],
            ),
        ],
    )
