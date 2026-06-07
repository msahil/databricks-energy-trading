"""
List and fetch Databricks Genie Spaces for the insights launcher pages.

Uses read-only Genie REST APIs (CAN VIEW on each space). Sample questions are
curated on the Dash pages — not loaded from ``serialized_space`` (that export
requires CAN EDIT).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

# Matches ``GENIE_SPACE_TITLE`` in modules/*/notebooks/genie_space_config.py
GENIE_TITLE_PREFIX_SHORT_TERM = "Energy Trading Genie - Short Term"
GENIE_TITLE_PREFIX_RENEWABLES = "Energy Trading Genie - Renewables"
GENIE_TITLE_PREFIX = GENIE_TITLE_PREFIX_SHORT_TERM


@dataclass(frozen=True)
class GenieSpaceOption:
    space_id: str
    title: str
    description: str | None


@dataclass(frozen=True)
class GenieSpaceDetail:
    space_id: str
    title: str
    description: str | None
    sample_questions: tuple[str, ...]
    workspace_url: str | None
    error: str | None = None


def _client() -> Any:
    from databricks.sdk import WorkspaceClient

    return WorkspaceClient()


def _workspace_host(client: Any) -> str:
    host = getattr(getattr(client, "config", None), "host", None) or ""
    return str(host).rstrip("/")


def _workspace_id(client: Any) -> str:
    """Workspace id for ``?o=`` on Genie room URLs (UI uses /genie/rooms/, not /genie/spaces/)."""
    ws_id = os.environ.get("DATABRICKS_WORKSPACE_ID", "").strip()
    if ws_id:
        return ws_id
    getter = getattr(client, "get_workspace_id", None)
    if callable(getter):
        try:
            return str(getter() or "").strip()
        except Exception:  # noqa: BLE001
            return ""
    return ""


def genie_room_url(client: Any, space_id: str) -> str | None:
    """Build the workspace UI link for opening a Genie Space in chat."""
    host = _workspace_host(client)
    sid = (space_id or "").strip()
    if not host or not sid:
        return None
    path = f"{host}/genie/rooms/{sid}"
    ws_id = _workspace_id(client)
    if ws_id:
        return f"{path}?{urlencode({'o': ws_id})}"
    return path


def _dropdown_label(opt: GenieSpaceOption) -> str:
    sid = opt.space_id
    suffix = f" ({sid[-8:]})" if sid else ""
    return f"{opt.title}{suffix}"


def _space_id_from_payload(sp: dict[str, Any]) -> str:
    return (sp.get("space_id") or sp.get("id") or "").strip()


def _list_spaces_page(client: Any, *, page_token: str | None = None) -> tuple[list[dict[str, Any]], str | None]:
    """List one page of Genie spaces via REST (works across SDK versions in Databricks Apps)."""
    query: dict[str, str] = {}
    if page_token:
        query["page_token"] = page_token
    res = client.api_client.do(
        "GET",
        "/api/2.0/genie/spaces",
        query=query or None,
        headers={"Accept": "application/json"},
    )
    if not isinstance(res, dict):
        return [], None
    spaces = res.get("spaces") or []
    if not isinstance(spaces, list):
        spaces = []
    next_token = (res.get("next_page_token") or "").strip() or None
    return spaces, next_token


def list_genie_spaces(title_prefix: str) -> tuple[list[GenieSpaceOption], str | None]:
    """Return spaces whose title starts with ``title_prefix``, sorted by title."""
    prefix = (title_prefix or "").strip()
    try:
        w = _client()
        page_token = None
        matches: list[GenieSpaceOption] = []
        while True:
            spaces, page_token = _list_spaces_page(w, page_token=page_token)
            for sp in spaces:
                if not isinstance(sp, dict):
                    continue
                title = (sp.get("title") or "").strip()
                if not prefix or not title.startswith(prefix):
                    continue
                space_id = _space_id_from_payload(sp)
                if not space_id:
                    continue
                desc = (sp.get("description") or "").strip() or None
                matches.append(GenieSpaceOption(space_id=space_id, title=title, description=desc))
            if not page_token:
                break
        matches.sort(key=lambda o: (o.title, o.space_id))
        return matches, None
    except Exception as exc:  # noqa: BLE001 — surface auth/API errors in the UI
        return [], str(exc)


def list_short_term_genie_spaces() -> tuple[list[GenieSpaceOption], str | None]:
    """Short-term Genie spaces (``Energy Trading Genie - Short Term``)."""
    return list_genie_spaces(GENIE_TITLE_PREFIX_SHORT_TERM)


def list_renewables_genie_spaces() -> tuple[list[GenieSpaceOption], str | None]:
    """Renewables / volume-forecast Genie spaces (``Energy Trading Genie - Renewables``)."""
    return list_genie_spaces(GENIE_TITLE_PREFIX_RENEWABLES)


def get_genie_space_detail(space_id: str) -> GenieSpaceDetail:
    """Fetch title, description, and workspace link for a space (CAN VIEW)."""
    space_id = (space_id or "").strip()
    if not space_id:
        return GenieSpaceDetail(
            space_id="",
            title="",
            description=None,
            sample_questions=(),
            workspace_url=None,
            error="No Genie space selected.",
        )
    try:
        w = _client()
        res = w.api_client.do(
            "GET",
            f"/api/2.0/genie/spaces/{space_id}",
            headers={"Accept": "application/json"},
        )
        title = (res.get("title") or "").strip()
        description = (res.get("description") or "").strip() or None
        workspace_url = genie_room_url(w, space_id)
        return GenieSpaceDetail(
            space_id=space_id,
            title=title,
            description=description,
            sample_questions=(),
            workspace_url=workspace_url,
        )
    except Exception as exc:  # noqa: BLE001
        return GenieSpaceDetail(
            space_id=space_id,
            title="",
            description=None,
            sample_questions=(),
            workspace_url=None,
            error=str(exc),
        )


def options_for_dropdown(spaces: list[GenieSpaceOption]) -> list[dict[str, str]]:
    return [{"label": _dropdown_label(s), "value": s.space_id} for s in spaces]
