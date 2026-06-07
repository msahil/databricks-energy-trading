"""
Run SQL against Unity Catalog via the Databricks Statement Execution API.

The warehouse id comes from the app header dropdown (`sql-warehouse-dropdown` in app.py).
Catalog/schema default to DEMO_UC_CATALOG / DEMO_UC_SCHEMA (or DEMO_UC_LOCATION as catalog.schema).

Capability pages should call run_sql via app.uc_pages.run_uc_sql so catalog, schema, and
warehouse selection stay consistent.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any


def default_catalog_schema() -> tuple[str, str]:
    loc = os.environ.get("DEMO_UC_LOCATION", "").strip()
    if loc and "." in loc:
        a, b = loc.split(".", 1)
        return a.strip(), b.strip()
    # Match demo data job defaults (databricks.yml / energy_trading_demo_data).
    cat = os.environ.get("DEMO_UC_CATALOG", "energy_utilities").strip() or "energy_utilities"
    sch = os.environ.get("DEMO_UC_SCHEMA", "energy_trading2").strip() or "energy_trading2"
    return cat, sch


def full_table(catalog: str, schema: str, name: str) -> str:
    def q(x: str) -> str:
        return "`" + x.replace("`", "``") + "`"

    return f"{q(catalog)}.{q(schema)}.{q(name)}"


@dataclass
class SqlResult:
    ok: bool
    columns: list[str]
    rows: list[list[Any]]
    error: str | None = None


def _fix_collect_chunks(w: Any, statement_id: str, first: Any) -> tuple[list[list[Any]], Any]:
    from databricks.sdk.service.sql import ResultData

    chunks: list[ResultData] = []
    if first.result:
        chunks.append(first.result)
    next_idx = first.result.next_chunk_index if first.result else None
    while next_idx is not None:
        ch = w.statement_execution.get_statement_result_chunk_n(statement_id, next_idx)
        chunks.append(ch)
        next_idx = ch.next_chunk_index
    all_rows: list[list[Any]] = []
    for ch in chunks:
        if ch.data_array:
            all_rows.extend(ch.data_array)
    return all_rows, first.manifest


def _poll_until_done(w: Any, statement_id: str) -> Any:
    from databricks.sdk.service.sql import StatementState

    deadline = time.time() + 120
    while time.time() < deadline:
        resp = w.statement_execution.get_statement(statement_id)
        st = resp.status.state if resp.status else None
        if st == StatementState.SUCCEEDED:
            return resp
        if st in (StatementState.FAILED, StatementState.CANCELED):
            err = resp.status.error if resp.status else None
            msg = err.message if err and getattr(err, "message", None) else str(st)
            raise RuntimeError(msg)
        time.sleep(0.4)
    raise TimeoutError("Statement did not finish within 120s.")


def run_sql(
    warehouse_id: str,
    sql: str,
    *,
    catalog: str | None = None,
    schema: str | None = None,
    row_limit: int = 2000,
) -> SqlResult:
    """
    Execute a read-only style statement; returns column names and data rows (strings in cells).
    """
    from databricks.sdk import WorkspaceClient
    from databricks.sdk.service.sql import StatementState

    sql = (sql or "").strip()
    if not sql:
        return SqlResult(ok=False, columns=[], rows=[], error="Empty SQL.")

    cat, sch = default_catalog_schema()
    cat = (catalog or "").strip() or cat
    sch = (schema or "").strip() or sch

    w = WorkspaceClient()
    try:
        resp = w.statement_execution.execute_statement(
            statement=sql,
            warehouse_id=warehouse_id,
            catalog=cat or None,
            schema=sch or None,
            row_limit=row_limit,
            wait_timeout="50s",
        )
    except Exception as exc:  # noqa: BLE001
        return SqlResult(ok=False, columns=[], rows=[], error=str(exc))

    st = resp.status.state if resp.status else None
    sid = resp.statement_id

    if st == StatementState.FAILED or st == StatementState.CANCELED:
        err = resp.status.error if resp.status else None
        msg = getattr(err, "message", None) or str(st)
        return SqlResult(ok=False, columns=[], rows=[], error=msg)

    if sid and st in (StatementState.PENDING, StatementState.RUNNING, None):
        try:
            resp = _poll_until_done(w, sid)
        except Exception as exc:  # noqa: BLE001
            return SqlResult(ok=False, columns=[], rows=[], error=str(exc))

    if resp.status and resp.status.state == StatementState.FAILED:
        err = resp.status.error if resp.status else None
        msg = getattr(err, "message", None) or "Statement failed"
        return SqlResult(ok=False, columns=[], rows=[], error=msg)

    if not sid:
        return SqlResult(ok=False, columns=[], rows=[], error="No statement id.")

    if resp.status and resp.status.state == StatementState.SUCCEEDED and sid and not resp.result:
        resp = w.statement_execution.get_statement(sid)

    all_rows, manifest = _fix_collect_chunks(w, sid, resp)
    columns: list[str] = []
    if manifest and manifest.schema and manifest.schema.columns:
        columns = [c.name or f"col_{i}" for i, c in enumerate(manifest.schema.columns)]
    if not columns and all_rows:
        columns = [f"col_{i}" for i in range(len(all_rows[0]))]

    def cell_str(v: Any) -> Any:
        if v is None:
            return ""
        return v

    norm: list[list[Any]] = []
    ncol = len(columns)
    for r in all_rows:
        padded = list(r) + [None] * max(0, ncol - len(r))
        norm.append([cell_str(x) for x in padded[:ncol]])

    return SqlResult(ok=True, columns=columns, rows=norm, error=None)
