"""
Genie Space config for renewables / volume-forecasting demo (wind, solar, accuracy).

Used by ``09_renewables_insights_genie.ipynb``. Self-contained (no cross-module imports).
"""

from __future__ import annotations

import json
import uuid
from typing import Any

GENIE_SPACE_TITLE = "Energy Trading Genie - Renewables"

GENIE_SPACE_DESCRIPTION = """
Natural-language SQL over governed renewables and volume-forecasting tables: wind and solar
generation forecasts, published net-volume supply legs, forecast accuracy, cost of error, and drift alerts.

Audience: renewables desk, risk, and management — fleet P50, curtailment and negative-price risk,
and the euro cost of forecast error without writing SQL. Demo data is synthetic.
"""

TEXT_INSTRUCTIONS = """Glossary:
- delivery_date: forecast / delivery day; join on this key across wind, solar, net volume, and accuracy tables.
- total_p50_mw (wind summary): average interval P50 aggregated to zone-day (demo naming).
- midday_peak_mw (solar): peak solar P50 in the daylight window.
- curtailment_risk (wind): LOW / MEDIUM / HIGH — fleet curtailment exposure.
- negative_price_risk (solar): LOW / MEDIUM / HIGH — midday surplus / cannibalization risk.
- leg (accuracy): WIND, SOLAR, NET, CONSUMPTION, INDUSTRIAL — error attribution.
- lead_bucket: DA, H+4, H+1, RT — error shrinks toward real time in the demo.
- cashout_eur: illustrative imbalance cost from volume_forecast_gold_cost_of_error.
- drift_status: STABLE, WATCH, DRIFT on volume_forecast_gold_drift_alerts.

Join hints:
- Wind / solar summaries: delivery_date + zone_code.
- Silver forecasts: latest forecast_ts per day (MAX(forecast_ts) for live cut).
- Net volume supply legs: wind_mw, solar_mw on volume_forecast_gold_net_volume where publication_status = 'PUBLISHED'.
"""

GENIE_TABLES: tuple[tuple[str, str], ...] = (
    ("volume_forecast_dim_zones", "Bidding zones DE, NL, FR, BE, AT."),
    ("volume_forecast_dim_wind_assets", "Onshore and offshore wind farm registry."),
    ("volume_forecast_dim_solar_assets", "Utility-scale solar farm registry."),
    ("volume_forecast_gold_wind_summary", "Wind desk KPIs: P50, peak, band, curtailment risk."),
    ("volume_forecast_gold_solar_summary", "Solar desk KPIs: P50, midday peak, negative-price risk, BTM netted."),
    ("volume_forecast_silver_wind_forecast", "Probabilistic wind P10/P50/P90 per asset × interval."),
    ("volume_forecast_silver_solar_forecast", "Probabilistic solar with clear-sky overlay per asset."),
    ("volume_forecast_gold_net_volume", "Published net volume — wind_mw and solar_mw supply legs."),
    ("volume_forecast_gold_accuracy_daily", "MAE / RMSE / bias by leg, zone, lead bucket."),
    ("volume_forecast_gold_cost_of_error", "Net forecast error translated to cash-out euros."),
    ("volume_forecast_gold_drift_alerts", "Error-distribution drift monitoring per leg × zone."),
)

SAMPLE_QUESTIONS: tuple[str, ...] = (
    "Show me renewables book performance — wind and solar P50, peaks, and risk flags on the latest delivery date.",
    "Which zones have HIGH wind curtailment risk on the latest delivery date?",
    "What is solar negative-price risk and midday peak by zone on the latest day?",
    "How much wind and solar supply is in the published net volume today?",
    "What is MAE and cash-out cost for the WIND and SOLAR legs at day-ahead lead time?",
    "Which renewables legs are in DRIFT or WATCH on the latest detected date?",
)

EXAMPLE_QUESTION_SQLS: tuple[tuple[str, str], ...] = (
    (
        "Renewables book performance latest day",
        """SELECT w.delivery_date, w.zone_code,
       w.total_p50_mw AS wind_avg_p50_mw, w.peak_mw AS wind_peak_mw, w.curtailment_risk,
       s.total_p50_mw AS solar_avg_p50_mw, s.midday_peak_mw, s.negative_price_risk
FROM {fq}.volume_forecast_gold_wind_summary w
JOIN {fq}.volume_forecast_gold_solar_summary s
  ON w.delivery_date = s.delivery_date AND w.zone_code = s.zone_code
WHERE w.delivery_date = (SELECT MAX(delivery_date) FROM {fq}.volume_forecast_gold_wind_summary)
ORDER BY w.zone_code""",
    ),
    (
        "Published renewables supply in net volume",
        """SELECT delivery_date, zone_code,
       ROUND(AVG(wind_mw), 2) AS avg_wind_mw,
       ROUND(AVG(solar_mw), 2) AS avg_solar_mw,
       ROUND(AVG(total_supply_mw), 2) AS avg_total_supply_mw
FROM {fq}.volume_forecast_gold_net_volume
WHERE publication_status = 'PUBLISHED'
  AND delivery_date = (SELECT MAX(delivery_date) FROM {fq}.volume_forecast_gold_net_volume)
GROUP BY delivery_date, zone_code
ORDER BY zone_code""",
    ),
    (
        "Renewables accuracy and cost at DA",
        """SELECT leg, zone_code, ROUND(AVG(mae_mw), 3) AS mae_mw, ROUND(AVG(bias_mw), 3) AS bias_mw
FROM {fq}.volume_forecast_gold_accuracy_daily
WHERE leg IN ('WIND', 'SOLAR')
  AND lead_bucket = 'DA'
  AND delivery_date = (SELECT MAX(delivery_date) FROM {fq}.volume_forecast_gold_accuracy_daily)
GROUP BY leg, zone_code
ORDER BY leg, zone_code""",
    ),
    (
        "Drift alerts on renewables legs",
        """SELECT leg, zone_code, metric, drift_status, drift_pct, baseline_value, current_value
FROM {fq}.volume_forecast_gold_drift_alerts
WHERE leg IN ('WIND', 'SOLAR')
  AND detected_date = (SELECT MAX(detected_date) FROM {fq}.volume_forecast_gold_drift_alerts)
ORDER BY CASE drift_status WHEN 'DRIFT' THEN 1 WHEN 'WATCH' THEN 2 ELSE 3 END, drift_pct DESC""",
    ),
)

METRIC_VIEW_SPECS: tuple[tuple[str, str, list[tuple[str, str]], list[tuple[str, str]]], ...] = (
    (
        "mv_vf_wind_summary",
        "volume_forecast_gold_wind_summary",
        [("Delivery Date", "delivery_date"), ("Zone", "zone_code")],
        [
            ("Wind P50 MW", "MAX(total_p50_mw)"),
            ("Wind Peak MW", "MAX(peak_mw)"),
            ("Curtailment Risk", "MAX(curtailment_risk)"),
        ],
    ),
    (
        "mv_vf_solar_summary",
        "volume_forecast_gold_solar_summary",
        [("Delivery Date", "delivery_date"), ("Zone", "zone_code")],
        [
            ("Solar P50 MW", "MAX(total_p50_mw)"),
            ("Midday Peak MW", "MAX(midday_peak_mw)"),
            ("Negative Price Risk", "MAX(negative_price_risk)"),
        ],
    ),
)


def _new_id() -> str:
    return uuid.uuid4().hex


_GENIE_JSON_HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
}


def _parse_genie_space_response(res: dict[str, Any]) -> Any:
    from databricks.sdk.service.dashboards import GenieSpace

    return GenieSpace.from_dict(res)


def create_genie_space_rest(
    client: Any,
    *,
    warehouse_id: str,
    serialized_space: str,
    title: str,
    description: str | None = None,
) -> Any:
    body: dict[str, Any] = {
        "warehouse_id": warehouse_id,
        "serialized_space": serialized_space,
        "title": title,
    }
    if description:
        body["description"] = description
    res = client.api_client.do(
        "POST",
        "/api/2.0/genie/spaces",
        body=body,
        headers=_GENIE_JSON_HEADERS,
    )
    return _parse_genie_space_response(res)


def update_genie_space_rest(
    client: Any,
    *,
    space_id: str,
    warehouse_id: str,
    serialized_space: str,
    title: str,
    description: str | None = None,
) -> Any:
    body: dict[str, Any] = {
        "warehouse_id": warehouse_id,
        "serialized_space": serialized_space,
        "title": title,
    }
    if description:
        body["description"] = description
    res = client.api_client.do(
        "PATCH",
        f"/api/2.0/genie/spaces/{space_id}",
        body=body,
        headers=_GENIE_JSON_HEADERS,
    )
    return _parse_genie_space_response(res)


def find_genie_space_id(client: Any, title: str) -> str | None:
    page_token = None
    target = title.strip()
    while True:
        resp = client.genie.list_spaces(page_token=page_token)
        for sp in resp.spaces or []:
            if (sp.title or "").strip() == target:
                return sp.space_id
        page_token = resp.next_page_token
        if not page_token:
            break
    return None


def provision_genie_space(
    client: Any,
    *,
    title: str,
    description: str,
    warehouse_id: str,
    serialized_space: str,
) -> tuple[Any, str]:
    genie = client.genie
    existing_id = find_genie_space_id(client, title)

    if existing_id:
        if hasattr(genie, "update_space"):
            space = genie.update_space(
                space_id=existing_id,
                serialized_space=serialized_space,
                title=title,
                description=description,
                warehouse_id=warehouse_id,
            )
        else:
            space = update_genie_space_rest(
                client,
                space_id=existing_id,
                warehouse_id=warehouse_id,
                serialized_space=serialized_space,
                title=title,
                description=description,
            )
        return space, "updated"

    if hasattr(genie, "create_space"):
        space = genie.create_space(
            warehouse_id=warehouse_id,
            serialized_space=serialized_space,
            title=title,
            description=description,
        )
    else:
        space = create_genie_space_rest(
            client,
            warehouse_id=warehouse_id,
            serialized_space=serialized_space,
            title=title,
            description=description,
        )
    return space, "created"


def metric_view_full_name(catalog: str, schema: str, view_suffix: str) -> str:
    return f"{catalog}.{schema}.{view_suffix}"


def build_metric_view_sql(catalog: str, schema: str, spec: tuple) -> str:
    view_suffix, source_table, dimensions, measures = spec
    source_ident = f"{catalog}.{schema}.{source_table}"
    view_fq = f"`{catalog}`.`{schema}`.`{view_suffix}`"
    dim_lines = "\n".join(f'  - name: {name}\n    expr: {expr}' for name, expr in dimensions)
    meas_lines = "\n".join(f'  - name: {name}\n    expr: {expr}' for name, expr in measures)
    yaml_body = f"""version: 1.1
comment: "Demo metric view on {source_table}"
source: {source_ident}
dimensions:
{dim_lines}
measures:
{meas_lines}
"""
    return (
        f"CREATE OR REPLACE VIEW {view_fq}\n"
        f"WITH METRICS\nLANGUAGE YAML\nAS $$\n{yaml_body}$$\n"
    )


def _sort_data_source_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(entries, key=lambda e: e["identifier"])


def _sort_by_id(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(entries, key=lambda e: e["id"])


def build_serialized_space(
    catalog: str,
    schema: str,
    *,
    include_metric_views: bool = True,
) -> str:
    table_entries = _sort_data_source_entries([
        {
            "identifier": f"{catalog}.{schema}.{table}",
            "description": [desc] if desc else [],
        }
        for table, desc in GENIE_TABLES
    ])
    metric_entries: list[dict[str, Any]] = []
    if include_metric_views:
        metric_entries = _sort_data_source_entries([
            {
                "identifier": metric_view_full_name(catalog, schema, view_suffix),
                "description": [f"Governed metrics on {source_table}."],
            }
            for view_suffix, source_table, _dims, _meas in METRIC_VIEW_SPECS
        ])

    sample_q = _sort_by_id([{"id": _new_id(), "question": [q]} for q in SAMPLE_QUESTIONS])
    example_sqls = _sort_by_id([
        {
            "id": _new_id(),
            "question": [question],
            "sql": [sql.format(fq=f"{catalog}.{schema}")],
        }
        for question, sql in EXAMPLE_QUESTION_SQLS
    ])
    text_instructions = _sort_by_id([
        {"id": _new_id(), "content": [TEXT_INSTRUCTIONS]},
    ])

    payload: dict[str, Any] = {
        "version": 2,
        "config": {"sample_questions": sample_q},
        "data_sources": {
            "tables": table_entries,
            "metric_views": metric_entries,
        },
        "instructions": {
            "text_instructions": text_instructions,
            "example_question_sqls": example_sqls,
        },
    }
    return json.dumps(payload)
