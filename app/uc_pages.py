"""
Shared patterns for Dash capability pages that query Unity Catalog.

All SQL runs through the header warehouse (`sql-warehouse-dropdown`) and
`uc_sql.run_sql` with catalog/schema from DEMO_UC_* env vars (see app.yaml).
"""

from __future__ import annotations

from typing import Any

from dash import html

import ui_icons as uicons
from uc_sql import SqlResult, default_catalog_schema, full_table, run_sql

# Global header control defined in app/app.py layout.
SQL_WAREHOUSE_DROPDOWN_ID = "sql-warehouse-dropdown"


def uc_location_label() -> str:
    cat, sch = default_catalog_schema()
    return f"{cat}.{sch}"


def fq(table_name: str) -> str:
    """Fully qualified `catalog`.`schema`.`table` for the demo UC location."""
    cat, sch = default_catalog_schema()
    return full_table(cat, sch, table_name)


def run_uc_sql(
    warehouse_id: str | None,
    sql: str,
    *,
    row_limit: int = 2000,
) -> SqlResult:
    """Execute SQL using the selected warehouse and default UC catalog/schema."""
    if not warehouse_id:
        return SqlResult(ok=False, columns=[], rows=[], error="No SQL warehouse selected.")
    cat, sch = default_catalog_schema()
    return run_sql(warehouse_id, sql, catalog=cat, schema=sch, row_limit=row_limit)


def warehouse_prompt(*, kind: str = "info") -> html.Div:
    """Shown when the header warehouse dropdown has no selection."""
    return html.Div(
        "Select a **running connection** in the header (top right), then refresh this page.",
        className=f"curve-alert curve-alert-{kind}",
    )


def data_context_strip(*, note: str = "Illustrative demo prices") -> html.Div:
    """Optional subtle banner — no catalog or table names."""
    return html.Div(
        className="uc-context-strip",
        children=[html.Span(note, className="uc-context-hint")],
    )


def sql_escape(value: str) -> str:
    return (value or "").replace("'", "''")


PRESENTER_LEAD_CAPABILITY = (
    "You are presenting to experienced energy traders — they respect clarity, not buzzwords. "
    "You do not need to be a trader yourself. Each note below is written as a short paragraph: "
    "read it aloud or paraphrase, but do not rush through one-liners. Cover section 1 (their pain), "
    "section 2 (why the business cares), then walk section 3 top to bottom while pointing at each widget."
)
PRESENTER_LEAD_GENIE = (
    "Use this after the dashboard pages in the module. You do not need SQL. The notes are descriptive "
    "on purpose — take your time, show traders they can ask desk questions in plain English against "
    "the same governed numbers the dashboards already showed."
)
_PRESENTER_MODAL_LEAD = PRESENTER_LEAD_CAPABILITY


def presenter_tip_button(button_id: str) -> html.Button:
    return html.Button(
        [
            html.Span(
                className="curve-presenter-tip-icon",
                children=html.Span("i", className="curve-presenter-tip-glyph"),
            ),
            html.Span("Presenter guide"),
        ],
        id=button_id,
        type="button",
        className="curve-presenter-tip-btn",
        title="Open presenter guide",
        **{"aria-haspopup": "dialog"},
    )


def presenter_modal(
    sections: tuple[tuple[str, tuple[str, ...]], ...],
    *,
    modal_id: str,
    close_id: str,
    backdrop_id: str,
    title_id: str,
    lead: str = _PRESENTER_MODAL_LEAD,
) -> html.Div:
    body_sections = [
        html.Section(
            className="curve-presenter-section",
            children=[
                html.H3(title, className="curve-presenter-section-title"),
                html.Div(
                    [html.P(item, className="curve-presenter-note") for item in bullets],
                    className="curve-presenter-notes",
                ),
            ],
        )
        for title, bullets in sections
    ]
    return html.Div(
        id=modal_id,
        className="curve-presenter-modal",
        **{"role": "dialog", "aria-modal": "true", "aria-labelledby": title_id},
        children=[
            html.Button(
                type="button",
                className="curve-presenter-modal-backdrop",
                id=backdrop_id,
                n_clicks=0,
                **{"aria-label": "Close presenter guide"},
            ),
            html.Div(
                className="curve-presenter-modal-panel",
                children=[
                    html.Div(
                        className="curve-presenter-modal-header",
                        children=[
                            html.H2("Presenter guide", id=title_id, className="curve-presenter-modal-title"),
                            html.Button("×", id=close_id, type="button", className="curve-presenter-modal-close"),
                        ],
                    ),
                    html.Div(
                        className="curve-presenter-modal-body",
                        children=[html.P(lead, className="curve-presenter-lead"), *body_sections],
                    ),
                ],
            ),
        ],
    )


def planned_capability_page(
    *,
    eyebrow: str,
    title: str,
    icon: str,
    summary: str,
    will_show: tuple[str, ...] = (),
) -> html.Div:
    """Lightweight 'planned' capability page so the sidebar route resolves before the
    full data-backed page exists. Replace with the real page when notebooks land."""
    body_children: list[Any] = []
    if will_show:
        body_children.append(html.P("Planned view:", className="curve-section-lead"))
        body_children.append(
            html.Ul(
                className="curve-list",
                children=[html.Li(item) for item in will_show],
            )
        )

    roadmap_lead = (
        "This capability is specified and on the build list. Once its seed notebook materialises "
        "the governed volume_forecast_* tables, this page will load them through the SQL warehouse "
        "selected in the header — no mock data."
    )

    return html.Div(
        className="page-curve",
        children=[
            html.Div(
                className="curve-page-hero",
                children=[
                    html.Div(
                        className="curve-page-hero-head",
                        children=[
                            html.Div(
                                className="curve-page-hero-top",
                                children=[
                                    html.Span(eyebrow, className="curve-page-eyebrow"),
                                    html.Span("Planned", className="curve-page-badge"),
                                ],
                            ),
                        ],
                    ),
                    uicons.hero_title(title, icon),
                    html.P(summary, className="curve-page-summary"),
                ],
            ),
            html.Div(
                className="curve-page-body",
                children=[capability_section("On the roadmap", roadmap_lead, *body_children)],
            ),
        ],
    )


def capability_section(title: str, lead: str, *children: Any) -> html.Section:
    """Section block with a trader-facing description under the title."""
    return html.Section(
        className="curve-section",
        children=[
            html.H2(title, className="curve-section-title"),
            html.P(lead, className="curve-section-lead"),
            *children,
        ],
    )


def resolve_dropdown_value(current: str | None, values: list[str]) -> str | None:
    """Keep a valid selection; otherwise default to the first option."""
    if not values:
        return None
    if current and current in values:
        return current
    return values[0]


def normalize_as_of(value: Any) -> str | None:
    """Normalize warehouse/API date cells to ``yyyy-MM-dd`` for filters."""
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    # DATE columns may arrive as 2025-05-20 or 2025-05-20T00:00:00.000+00:00
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:10]
    return s


def sql_as_of_predicate(column: str, as_of: str) -> str:
    """Serverless/SQL-warehouse-safe filter for a single calendar date."""
    d = normalize_as_of(as_of)
    if not d:
        return "1 = 0"
    return f"{column} = DATE '{sql_escape(d)}'"


def sql_delivery_date_predicate(column: str, delivery_date: str) -> str:
    """Serverless/SQL-warehouse-safe filter for a short-term trading delivery day."""
    return sql_as_of_predicate(column, delivery_date)


def plotly_legend(*, n_traces: int) -> dict[str, Any]:
    """Legend placement that avoids cramped single-line overflow in capability charts.

    Four or more traces → vertical legend outside the plot (right).
    Fewer traces → horizontal legend centred below the x-axis.
    """
    if n_traces >= 4:
        return {
            "orientation": "v",
            "yanchor": "top",
            "y": 1,
            "x": 1.02,
            "xanchor": "left",
            "font": {"size": 11},
            "bgcolor": "rgba(255,255,255,0.92)",
            "bordercolor": "rgba(15,23,42,0.08)",
            "borderwidth": 1,
        }
    return {
        "orientation": "h",
        "yanchor": "top",
        "y": -0.22,
        "x": 0.5,
        "xanchor": "center",
        "tracegroupgap": 14,
        "font": {"size": 11},
    }


def plotly_chart_margins(*, n_traces: int = 1, angled_x: bool = True) -> dict[str, int]:
    """Plot margins sized for ``plotly_legend`` and optional angled x labels."""
    bottom = 88 if angled_x else 52
    right = 108 if n_traces >= 4 else 16
    if n_traces < 4:
        bottom += 40
    return {"l": 48, "r": right, "t": 16, "b": bottom}
