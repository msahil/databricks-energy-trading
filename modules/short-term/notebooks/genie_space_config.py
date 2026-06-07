"""
Build Genie Space serialized config and UC metric views for short-term trading demo.

Used by ``04_trader_insights_genie.ipynb``. Requires Databricks SDK ``w.genie`` APIs.
"""

from __future__ import annotations

import json
import uuid
from typing import Any


GENIE_SPACE_TITLE = "Energy Trading Genie - Short Term"

GENIE_SPACE_DESCRIPTION = """
Natural-language SQL over governed Unity Catalog tables for a European prompt-and-spot desk demo:
near-delivery squaring, 24/7 control-tower operations, and DSR / VPP market access.

Audience: intraday traders and operators who need net position, gate status, imbalance cash-out,
fleet flex, dispatch verification, and REMIT context without writing SQL. All data is synthetic
and illustrative — not live market or regulatory data.
"""

TEXT_INSTRUCTIONS = """Glossary:
- delivery_date: trading / delivery day; join all short-term gold on this key unless interval grain is needed.
- interval_start / interval_index: 15-minute XBID delivery blocks (96 per day).
- gate_status OPEN vs CLOSED: from short_term_gold_squaring_actions — OPEN means squaring still allowed.
- net_delta_mw: residual long/short vs hedge; positive often means long physical.
- projected_cashout_eur: TSO imbalance penalty if nominations and metering stay misaligned.
- balance_state: EXPOSED / BALANCED from short_term_gold_portfolio_balance or control_tower_summary.
- dsr_contribution_mw: verified flex dispatch feeding the control-tower ribbon.
- verification_status on DSR dispatch: VERIFIED, UNDER_DELIVERED, PENDING.

Join hints:
- Squaring & imbalance: delivery_date + zone_code + interval_start.
- Control tower balance: delivery_date + interval_start; join short_term_dim_intervals for interval_index.
- Asset dispatch: delivery_date + interval_start + asset_id.
- DSR: dsr_asset_id to short_term_dim_dsr_assets; owner_id to short_term_dim_dsr_owners.
- Prefer metric views (mv_st_*) for KPI questions; use base gold tables for drill-down SQL."""

GENIE_TABLES: tuple[tuple[str, str], ...] = (
    ("short_term_dim_zones", "Bidding zones DE, NL, FR, BE, AT."),
    ("short_term_dim_assets", "Owned physical assets in the 1,000 MW book."),
    ("short_term_dim_intervals", "15-minute delivery interval spine."),
    ("short_term_gold_squaring_actions", "Recommended squaring per interval before gate close."),
    ("short_term_gold_near_delivery_summary", "Near-delivery desk headline KPIs."),
    ("short_term_gold_imbalance_exposure", "Projected cash-out by interval."),
    ("short_term_gold_backtest_runs", "Backtested squaring strategy results."),
    ("short_term_gold_portfolio_balance", "Control-tower balance ribbon (squaring + DSR)."),
    ("short_term_gold_asset_dispatch", "Per-asset dispatch recommendations."),
    ("short_term_silver_grid_frequency", "TSO frequency and balancing signals."),
    ("short_term_silver_market_gates", "Gate countdown and order-book depth."),
    ("short_term_gold_remit_events", "REMIT / outage event feed."),
    ("short_term_gold_copilot_recommendations", "Agentic copilot recommendations."),
    ("short_term_gold_control_tower_summary", "Shift headline, P&L, alerts."),
    ("short_term_dim_dsr_assets", "VPP / DSR asset registry."),
    ("short_term_dim_dsr_owners", "Aggregated asset owners."),
    ("short_term_silver_dsr_availability", "Fleet flex up/down by interval."),
    ("short_term_gold_dsr_bid_stack", "Prequalified bid stack per market."),
    ("short_term_gold_dsr_dispatch", "Dispatched and verified MW."),
    ("short_term_gold_dsr_settlement", "Per-owner settlement."),
    ("short_term_gold_dsr_summary", "DSR desk headline KPIs."),
)

SAMPLE_QUESTIONS: tuple[str, ...] = (
    "What is the net open position and projected cash-out on the latest delivery date?",
    "Which intervals still have OPEN gate status and a recommended squaring action in DE?",
    "Show severe forecast deviations for the latest trading day.",
    "What is the control-tower balance state and P&L since shift start?",
    "List critical REMIT events for the latest delivery date.",
    "What is the top copilot recommendation and expected P&L impact?",
    "How much flex up and flex down is available in the DSR fleet today?",
    "Which DSR markets are prequalified and how many MW are bid-ready?",
    "Show verified DSR dispatch events triggered by negative prices or scarcity.",
    "How much market revenue was captured and paid to owners on the latest day?",
)

EXAMPLE_QUESTION_SQLS: tuple[tuple[str, str], ...] = (
    (
        "Net open position and projected cash-out on latest day",
        """SELECT delivery_date, net_open_position_mw, projected_cashout_eur, headline
FROM {fq}.short_term_gold_near_delivery_summary
ORDER BY delivery_date DESC
LIMIT 1""",
    ),
    (
        "OPEN squaring actions in DE",
        """SELECT interval_start, net_delta_mw, recommended_side, recommended_mw, gate_status
FROM {fq}.short_term_gold_squaring_actions
WHERE zone_code = 'DE' AND gate_status = 'OPEN'
  AND delivery_date = (SELECT MAX(delivery_date) FROM {fq}.short_term_gold_squaring_actions)
ORDER BY interval_start
LIMIT 20""",
    ),
    (
        "Control tower balance state and shift P&L",
        """SELECT delivery_date, balance_state, pnl_since_shift_eur, n_open_alerts, headline
FROM {fq}.short_term_gold_control_tower_summary
ORDER BY delivery_date DESC
LIMIT 1""",
    ),
    (
        "DSR fleet revenue and dispatch on latest day",
        """SELECT delivery_date, total_dispatched_mwh, total_market_revenue_eur, avg_delivery_ratio, headline
FROM {fq}.short_term_gold_dsr_summary
ORDER BY delivery_date DESC
LIMIT 1""",
    ),
)

METRIC_VIEW_SPECS: tuple[tuple[str, str, list[tuple[str, str]], list[tuple[str, str]]], ...] = (
    (
        "mv_st_near_delivery_summary",
        "short_term_gold_near_delivery_summary",
        [("Delivery Date", "delivery_date")],
        [
            ("Net Open MW", "MAX(net_open_position_mw)"),
            ("Projected Cashout EUR", "MAX(projected_cashout_eur)"),
            ("Severe Deviations", "MAX(n_severe_deviations)"),
        ],
    ),
    (
        "mv_st_squaring_actions",
        "short_term_gold_squaring_actions",
        [
            ("Delivery Date", "delivery_date"),
            ("Zone", "zone_code"),
            ("Gate Status", "gate_status"),
        ],
        [
            ("Net Delta MW", "SUM(net_delta_mw)"),
            ("Recommended MW", "SUM(recommended_mw)"),
        ],
    ),
    (
        "mv_st_portfolio_balance",
        "short_term_gold_portfolio_balance",
        [
            ("Delivery Date", "delivery_date"),
            ("Balance State", "balance_state"),
        ],
        [
            ("Net Position MW", "SUM(net_position_mw)"),
            ("DSR Contribution MW", "SUM(dsr_contribution_mw)"),
        ],
    ),
    (
        "mv_st_dsr_summary",
        "short_term_gold_dsr_summary",
        [("Delivery Date", "delivery_date")],
        [
            ("Market Revenue EUR", "MAX(total_market_revenue_eur)"),
            ("Dispatched MWh", "MAX(total_dispatched_mwh)"),
            ("Flex Up MW", "MAX(total_available_up_mw)"),
        ],
    ),
    (
        "mv_st_dsr_dispatch",
        "short_term_gold_dsr_dispatch",
        [
            ("Delivery Date", "delivery_date"),
            ("Market", "market"),
            ("Verification", "verification_status"),
        ],
        [
            ("Delivered MW", "SUM(delivered_mw)"),
            ("Avg Delivery Ratio", "AVG(delivery_ratio)"),
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
    """POST /api/2.0/genie/spaces — for SDK versions without ``genie.create_space``."""
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
    """PATCH /api/2.0/genie/spaces/{space_id} — for SDK without ``genie.update_space``."""
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


def provision_genie_space(
    client: Any,
    *,
    title: str,
    description: str,
    warehouse_id: str,
    serialized_space: str,
) -> tuple[Any, str]:
    """Create or update a Genie Space by title. Returns ``(space, operation)``."""
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


def find_genie_space_id(client: Any, title: str) -> str | None:
    """Return ``space_id`` for an exact title match (paginates ``list_spaces``)."""
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


def uc_schema_fq(catalog: str, schema: str) -> str:
    """Qualified catalog.schema (backticks). Not the notebook ``fq(table)`` helper."""
    return f"`{catalog}`.`{schema}`"


def metric_view_full_name(catalog: str, schema: str, view_suffix: str) -> str:
    return f"{catalog}.{schema}.{view_suffix}"


def build_metric_view_sql(catalog: str, schema: str, spec: tuple) -> str:
    view_suffix, source_table, dimensions, measures = spec
    # YAML source must be catalog.schema.table (no backticks) per UC metric view spec.
    source_ident = f"{catalog}.{schema}.{source_table}"
    view_fq = f"{uc_schema_fq(catalog, schema)}.`{view_suffix}`"
    dim_lines = "\n".join(
        f'  - name: {name}\n    expr: {expr}' for name, expr in dimensions
    )
    meas_lines = "\n".join(
        f'  - name: {name}\n    expr: {expr}' for name, expr in measures
    )
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
    """Genie export proto requires tables/metric_views sorted by ``identifier``."""
    return sorted(entries, key=lambda e: e["identifier"])


def _sort_by_id(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Genie export proto requires instruction arrays sorted by ``id``."""
    return sorted(entries, key=lambda e: e["id"])


def build_serialized_space(
    catalog: str,
    schema: str,
    *,
    include_metric_views: bool = True,
) -> str:
    """Genie API v2 serialized_space JSON string."""
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

    sample_q = _sort_by_id([
        {"id": _new_id(), "question": [q]} for q in SAMPLE_QUESTIONS
    ])
    example_sqls = _sort_by_id([
        {
            "id": _new_id(),
            "question": [question],
            "sql": [sql.format(fq=f"{catalog}.{schema}")],
        }
        for question, sql in EXAMPLE_QUESTION_SQLS
    ])
    text_instructions = _sort_by_id([
        {
            "id": _new_id(),
            "content": [TEXT_INSTRUCTIONS],
        }
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


def all_table_identifiers(catalog: str, schema: str, *, include_metric_views: bool = True) -> list[str]:
    ids = [f"{catalog}.{schema}.{t}" for t, _ in GENIE_TABLES]
    if include_metric_views:
        ids.extend(
            metric_view_full_name(catalog, schema, suffix)
            for suffix, _, _, _ in METRIC_VIEW_SPECS
        )
    return ids
