"""
Energy Trading demo — Databricks App UI.

Utility CSS is loaded from a CDN; app-specific styles live in `assets/custom.css`.
"""

from __future__ import annotations

import os
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
    Append warehouse dropdown CSS at end of <body> so it wins over:
    - Dash/webpack styles injected for react-select after page load
    - Tailwind CDN (preflight / utilities) when it loads after assets
    """
    css_path = Path(__file__).resolve().parent / "warehouse_dropdown_menu.css"
    try:
        block = css_path.read_text(encoding="utf-8")
    except OSError:
        block = "/* warehouse_dropdown_menu.css missing */\n"
    return _DASH_INDEX_HTML.replace(
        "</body>",
        f'<style id="warehouse-dropdown-overrides">\n{block}\n</style>\n</body>',
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


# ---------------------------------------------------------------------------
# App & WSGI server (required name `server` for gunicorn app:server)
# ---------------------------------------------------------------------------
app = Dash(
    __name__,
    use_pages=True,
    title="Energy Trading System",
    external_scripts=["https://cdn.tailwindcss.com"],
    external_stylesheets=[
        "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap",
    ],
    suppress_callback_exceptions=True,
    index_string=_build_index_string(),
)


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
                                            options=[],
                                            value=None,
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
                dash.page_container,
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
    options = [{"label": f"{name}  ·  {wid}", "value": wid} for wid, name in rows]
    ids = {r[0] for r in rows}

    if not rows:
        if _PREV_WAREHOUSE_SNAPSHOT == tuple():
            raise PreventUpdate
        _PREV_WAREHOUSE_SNAPSHOT = tuple()
        return [], None

    if snapshot == _PREV_WAREHOUSE_SNAPSHOT:
        if current_value and current_value in ids:
            raise PreventUpdate
        return options, rows[0][0]

    _PREV_WAREHOUSE_SNAPSHOT = snapshot
    if current_value and current_value in ids:
        return options, current_value
    return options, rows[0][0]


# Last fetched warehouse list — used to skip re-outputting dropdown props when nothing changed
# (re-sending options/value every 60s can re-trigger react-select and page callbacks).
_PREV_WAREHOUSE_SNAPSHOT: tuple[tuple[str, str], ...] | None = None

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
    """Local `python app.py` only. Production uses gunicorn (app.yaml); keep debug off unless opted in."""
    v = os.environ.get("DASH_DEBUG", "").strip().lower()
    if v in ("1", "true", "yes", "on"):
        return True
    if v in ("0", "false", "no", "off"):
        return False
    return False


if __name__ == "__main__":
    port = _port()
    debug = _debug_enabled()
    print(f"\n  Open: http://127.0.0.1:{port}/\n  (server must stay running; Ctrl+C to stop)\n")
    if debug:
        print("  Debug: ON — auto-reload; set DASH_DEBUG=false or unset to run in production mode.\n")
    app.run(host="0.0.0.0", port=port, debug=debug, dev_tools_hot_reload=debug)
