"""
Energy Trading demo — Databricks App UI.

Utility CSS is loaded from a CDN; app-specific styles live in `assets/custom.css`.
"""

from __future__ import annotations

import importlib
import os
import warnings
from pathlib import Path

import dash
from dash import Dash, Input, Output, State, callback, dcc, html
from dash.exceptions import PreventUpdate
from werkzeug.middleware.proxy_fix import ProxyFix

import shared_ui as su

try:
    from dash.dash import _default_index as _DASH_INDEX_HTML
except ImportError:  # pragma: no cover
    _DASH_INDEX_HTML = """<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
    </head>
    <body>
        <!--[if IE]><script>
        alert("Dash v2.7+ does not support Internet Explorer. Please use a newer browser.");
        </script><![endif]-->
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>"""


def _build_index_string() -> str:
    """
    Append react-select override CSS at end of <body> so it wins over:
    - Dash/webpack styles injected for react-select after page load
    - Tailwind CDN (preflight / utilities) when it loads after assets
    Files: warehouse_dropdown_menu.css (header), toolbar_dropdown_menu.css (pages).
    """
    app_dir = Path(__file__).resolve().parent
    blocks: list[str] = []
    for name in (
        "warehouse_dropdown_menu.css",
        "toolbar_dropdown_menu.css",
        "dip_arch_guard.css",
    ):
        css_path = app_dir / name
        try:
            blocks.append(css_path.read_text(encoding="utf-8"))
        except OSError:
            blocks.append(f"/* {name} missing */\n")
    combined = "\n".join(blocks)
    return _DASH_INDEX_HTML.replace(
        "</body>",
        f'<style id="app-body-overrides">\n{combined}\n</style>\n</body>',
    )

# ---------------------------------------------------------------------------
# Databricks: SQL warehouses (header selector)
# ---------------------------------------------------------------------------


def _fetch_running_sql_warehouses() -> list[tuple[str, str]]:
    """
    List SQL warehouses in the current workspace with state RUNNING.
    Returns list of (warehouse_id, display_name), sorted by name.

    Uses paginated GET /api/2.0/sql/warehouses with page_token. The SDK's
    ``w.warehouses.list()`` only returns the first page and omits further results.
    """
    from databricks.sdk import WorkspaceClient
    from databricks.sdk.service.sql import EndpointInfo, State

    w = WorkspaceClient()
    rows: list[tuple[str, str]] = []
    page_token: str | None = None
    headers = {"Accept": "application/json"}
    # Safety cap — each page is small; typical workspaces need only a few requests.
    for _ in range(500):
        query: dict[str, str] = {}
        if page_token:
            query["page_token"] = page_token
        raw = w.api_client.do("GET", "/api/2.0/sql/warehouses", query=query or None, headers=headers)
        if not isinstance(raw, dict):
            break
        for wh_dict in raw.get("warehouses") or []:
            wh = EndpointInfo.from_dict(wh_dict)
            if wh.state != State.RUNNING:
                continue
            wid = (wh.id or "").strip()
            name = (wh.name or wid or "SQL warehouse").strip()
            rows.append((wid, name))
        page_token = (raw.get("next_page_token") or "").strip() or None
        if not page_token:
            break
    rows.sort(key=lambda t: t[1].lower())
    return rows


def _warehouse_dropdown_options(rows: list[tuple[str, str]]) -> list[dict[str, str]]:
    return [{"label": f"{name}  ·  {wid}", "value": wid} for wid, name in rows]


def _resolve_warehouse_value(
    current_value: str | None, rows: list[tuple[str, str]]
) -> str | None:
    """Keep a valid selection; otherwise default to the first running warehouse."""
    if not rows:
        return None
    ids = {r[0] for r in rows}
    if current_value and current_value in ids:
        return current_value
    return rows[0][0]


def _load_initial_warehouses() -> tuple[list[dict[str, str]], str | None, tuple[tuple[str, str], ...]]:
    try:
        rows = _fetch_running_sql_warehouses()
    except Exception:
        return [], None, tuple()
    return _warehouse_dropdown_options(rows), _resolve_warehouse_value(None, rows), tuple(rows)


# Snapshot + layout defaults — first running warehouse selected on cold start.
_PREV_WAREHOUSE_SNAPSHOT: tuple[tuple[str, str], ...] | None = None
_INITIAL_WH_OPTIONS, _INITIAL_WH_VALUE, _INITIAL_WH_SNAPSHOT = _load_initial_warehouses()
_PREV_WAREHOUSE_SNAPSHOT = _INITIAL_WH_SNAPSHOT

_APP_DIR = Path(__file__).resolve().parent
_PAGES_DIR = _APP_DIR / "pages"
# Every route the sidebar links to; validated at startup so missing pages are obvious in logs.
_REQUIRED_PAGE_MODULES = (
    "pages.home",
    "pages.short_term_overview",
    "pages.short_term_near_delivery",
    "pages.short_term_control_tower",
    "pages.short_term_dsr",
    "pages.short_term_insights",
    "pages.volume_forecast_overview",
    "pages.volume_forecast_consumption_short_term",
    "pages.volume_forecast_consumption_long_term",
    "pages.volume_forecast_industry",
    "pages.volume_forecast_smart_metering",
    "pages.volume_forecast_wind",
    "pages.volume_forecast_solar",
    "pages.volume_forecast_publication",
    "pages.volume_forecast_accuracy",
    "pages.volume_forecast_insights",
)
_REQUIRED_PAGE_PATHS = (
    "/",
    "/short-term/overview",
    "/short-term/near-delivery",
    "/short-term/control-tower",
    "/short-term/dsr",
    "/short-term/insights",
    "/volume-forecasting/overview",
    "/volume-forecasting/consumption-short-term",
    "/volume-forecasting/consumption-long-term",
    "/volume-forecasting/industry",
    "/volume-forecasting/smart-metering",
    "/volume-forecasting/wind",
    "/volume-forecasting/solar",
    "/volume-forecasting/publication",
    "/volume-forecasting/accuracy",
    "/volume-forecasting/insights",
)


def _validate_page_registry() -> None:
    from dash import page_registry

    paths = {p.get("path") for p in page_registry.values()}
    missing_paths = [p for p in _REQUIRED_PAGE_PATHS if p not in paths]
    if missing_paths:
        warnings.warn(
            "Dash page registry is missing routes "
            f"{missing_paths}. Restart the app after adding files under app/pages/.",
            stacklevel=2,
        )


# ---------------------------------------------------------------------------
# App & WSGI server (required name `server` for gunicorn app:server)
# ---------------------------------------------------------------------------
app = Dash(
    __name__,
    use_pages=True,
    pages_folder=str(_PAGES_DIR),
    title="Energy Trading System",
    external_scripts=[
        "https://cdn.tailwindcss.com",
        "https://unpkg.com/lucide@0.469.0/dist/umd/lucide.min.js",
    ],
    external_stylesheets=[
        "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap",
    ],
    suppress_callback_exceptions=True,
    index_string=_build_index_string(),
)

for _page_module in _REQUIRED_PAGE_MODULES:
    importlib.import_module(_page_module)
_validate_page_registry()


app.layout = html.Div(
    className="app-page-bg flex min-h-screen",
    children=[
        su.sidebar(app.get_asset_url("databricks-header-logo.png")),
        html.Div(
            className="flex min-h-screen min-w-0 w-full flex-1 flex-col",
            children=[
                html.Div(
                    className="hero-brand flex h-[60px] min-h-[60px] max-h-[60px] w-full shrink-0 items-center justify-start py-0 box-border",
                    children=[
                        html.Div(
                            className="hero-inner flex h-full w-full max-w-none flex-row items-center justify-between gap-2 px-4 sm:gap-4 lg:px-6",
                            children=[
                                html.Div(
                                    className="min-w-0 flex-1 pr-2",
                                    children=[
                                        html.H1(
                                            "Energy Trading System",
                                            className="hero-title truncate text-left text-lg font-bold leading-none tracking-tight sm:text-xl",
                                        ),
                                    ],
                                ),
                                html.Div(
                                    className="warehouse-dd flex shrink-0 flex-row items-center gap-2 sm:gap-3",
                                    children=[
                                        html.Span(
                                            "SQL warehouse (running)",
                                            className="hidden whitespace-nowrap text-[10px] font-semibold uppercase tracking-wide text-white/85 sm:inline md:text-[11px]",
                                        ),
                                        dcc.Dropdown(
                                            id="sql-warehouse-dropdown",
                                            options=_INITIAL_WH_OPTIONS,
                                            value=_INITIAL_WH_VALUE,
                                            placeholder="No running warehouses",
                                            clearable=False,
                                            searchable=False,
                                            persistence=True,
                                            persistence_type="local",
                                            persisted_props=["value"],
                                            className="warehouse-sql-select max-w-none text-sm",
                                            maxHeight=260,
                                            style={
                                                "width": "min(36rem, min(42vw, calc(100vw - 2rem)))",
                                                "minWidth": "min(12rem, 100%)",
                                                "maxWidth": "min(36rem, min(42vw, calc(100vw - 2rem)))",
                                                "boxSizing": "border-box",
                                            },
                                        ),
                                        dcc.Interval(
                                            id="warehouse-refresh-interval",
                                            interval=60_000,
                                            n_intervals=0,
                                        ),
                                    ],
                                ),
                            ],
                        )
                    ],
                ),
                html.Main(
                    className="flex-1 px-4 py-6 sm:px-6 lg:px-8",
                    children=dash.page_container,
                ),
            ],
        ),
    ],
)


@callback(
    Output("sql-warehouse-dropdown", "options"),
    Output("sql-warehouse-dropdown", "value"),
    Input("warehouse-refresh-interval", "n_intervals"),
    State("sql-warehouse-dropdown", "value"),
)
def _sync_warehouse_dropdown(_n: int, current_value: str | None) -> tuple[list[dict[str, str]], str | None]:
    global _PREV_WAREHOUSE_SNAPSHOT
    try:
        rows = _fetch_running_sql_warehouses()
    except Exception:
        _PREV_WAREHOUSE_SNAPSHOT = None
        return [], None

    snapshot = tuple(rows)
    options = _warehouse_dropdown_options(rows)
    resolved = _resolve_warehouse_value(current_value, rows)

    if not rows:
        if _PREV_WAREHOUSE_SNAPSHOT == tuple():
            raise PreventUpdate
        _PREV_WAREHOUSE_SNAPSHOT = tuple()
        return [], None

    if snapshot == _PREV_WAREHOUSE_SNAPSHOT and resolved == current_value:
        raise PreventUpdate

    _PREV_WAREHOUSE_SNAPSHOT = snapshot
    return options, resolved

server = app.server
server.wsgi_app = ProxyFix(server.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1, x_prefix=1)


def _port() -> int:
    for key in ("PORT", "DATABRICKS_APP_PORT"):
        raw = os.environ.get(key)
        if raw:
            try:
                return int(raw)
            except ValueError:
                pass
    return 8050


def _debug_enabled() -> bool:
    """Dash development mode (debug UI, dev tools). Opt out with DASH_DEBUG=false."""
    v = os.environ.get("DASH_DEBUG", "").strip().lower()
    if v in ("0", "false", "no", "off"):
        return False
    if v in ("1", "true", "yes", "on"):
        return True
    return True


if __name__ == "__main__":
    port = _port()
    debug = _debug_enabled()
    print(f"\n  Open: http://127.0.0.1:{port}/\n  (server must stay running; Ctrl+C to stop)\n")
    if debug:
        print("  Debug: ON — auto-reload enabled; set DASH_DEBUG=false for production mode.\n")
    app.run(host="0.0.0.0", port=port, debug=debug, dev_tools_hot_reload=debug)
