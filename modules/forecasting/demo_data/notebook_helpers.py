"""
Shared helpers for Databricks / local Spark demo notebooks.

- Resolves `demo_data` on `sys.path` so `import synthetic_generators` works.
- Writes **Delta** tables to Unity Catalog at the catalog/schema from `modules/forecasting/README.md`
  (`energy_utilities.energy_trading2` by default), overridable via env vars.

On Databricks runtimes, writes use Delta `saveAsTable(full_name)` and do **not** fall back to CSV
unless `DEMO_ALLOW_CSV_FALLBACK=1`. Locally (no Spark), CSV is written under `./_demo_output/`.
"""

from __future__ import annotations

import csv
import os
import sys
from pathlib import Path
from typing import Any, Iterable, List, Optional, Sequence, Tuple, Union

Rows = Union[List[Tuple[Any, ...]], List[tuple]]

# Must match `unity_catalog.schemas` in modules/forecasting/README.md (first entry).
_DEFAULT_CATALOG = "energy_utilities"
_DEFAULT_SCHEMA = "energy_trading2"

_UC_SCHEMA_ENSURED = False


def demo_data_dir() -> Path:
    """Directory containing `synthetic_generators.py` (this file's parent)."""
    return Path(__file__).resolve().parent


def ensure_demo_data_on_path() -> Path:
    """
    Ensure `demo_data` Python modules are on ``sys.path``.

    - **Local:** uses this file's directory (repo checkout).
    - **Databricks workspace:** if notebooks live under ``.../notebooks/`` and ``demo_data/``
      is a sibling folder in the same workspace project (see upload runbook), resolves
      ``/Workspace/.../demo_data`` via ``dbutils`` notebook path or ``DEMO_DATA_WORKSPACE_PATH``.
    - **Databricks Repos:** if the path contains ``Repos`` and ``forecasting``, uses
      ``.../modules/forecasting/demo_data``.
    """
    d = demo_data_dir()
    p = str(d)
    if p not in sys.path:
        sys.path.insert(0, p)

    env_w = os.environ.get("DEMO_DATA_WORKSPACE_PATH", "").strip()
    if env_w and env_w not in sys.path:
        sys.path.insert(0, env_w)

    try:
        nb = dbutils.notebook.entry_point.getDbutils().notebook().getContext().notebookPath().get()  # type: ignore[name-defined]  # noqa: F821
    except NameError:
        nb = None
    except Exception:
        nb = None
    if nb:
        nbp = Path(nb)
        parts = nbp.parts
        if "Repos" in parts and "forecasting" in parts:
            i = parts.index("forecasting")
            ws_demo = Path(*parts[: i + 1]) / "demo_data"
        elif "notebooks" in parts:
            ws_demo = nbp.parent.parent / "demo_data"
        else:
            ws_demo = nbp.parent / "demo_data"
        ws_str = str(ws_demo)
        if ws_str not in sys.path:
            sys.path.insert(0, ws_str)
        if ws_demo.exists():
            return ws_demo

    return d


def catalog_schema() -> tuple[str, str]:
    """
    Return (catalog, schema) for demo Delta tables.

    Override with `DEMO_UC_LOCATION=energy_utilities.energy_trading2` or
    `DEMO_UC_CATALOG` / `DEMO_UC_SCHEMA` (see README.md).
    """
    loc = os.environ.get("DEMO_UC_LOCATION", "").strip()
    if loc and "." in loc:
        parts = loc.split(".", 1)
        return parts[0].strip(), parts[1].strip()
    cat = os.environ.get("DEMO_UC_CATALOG", _DEFAULT_CATALOG).strip()
    sch = os.environ.get("DEMO_UC_SCHEMA", _DEFAULT_SCHEMA).strip()
    return cat, sch


def _quote_uc_ident(name: str) -> str:
    """Quote a Unity Catalog identifier for Spark SQL (hyphens, reserved words, etc.)."""
    return "`" + name.replace("`", "``") + "`"


def full_table_name(short_name: str) -> str:
    cat, sch = catalog_schema()
    return f"{_quote_uc_ident(cat)}.{_quote_uc_ident(sch)}.{_quote_uc_ident(short_name)}"


def is_databricks_runtime() -> bool:
    return bool(os.environ.get("DATABRICKS_RUNTIME_VERSION"))


def allow_csv_fallback() -> bool:
    if is_databricks_runtime():
        return os.environ.get("DEMO_ALLOW_CSV_FALLBACK", "").strip().lower() in ("1", "true", "yes")
    return True


def ensure_uc_schema(spark) -> None:
    """
    Ensure the Unity Catalog schema exists (CREATE SCHEMA IF NOT EXISTS).

    No-op if spark is None. Safe to call before every demo notebook; runs once per process.
    If CREATE fails (e.g. insufficient privilege), a warning is printed; ``saveAsTable`` may
    still succeed when the schema already exists.
    """
    global _UC_SCHEMA_ENSURED
    if spark is None or _UC_SCHEMA_ENSURED:
        return
    cat, sch = catalog_schema()
    try:
        spark.sql(f"CREATE SCHEMA IF NOT EXISTS {_quote_uc_ident(cat)}.{_quote_uc_ident(sch)}")
    except Exception as e:
        print(f"[ensure_uc_schema] CREATE SCHEMA IF NOT EXISTS {_quote_uc_ident(cat)}.{_quote_uc_ident(sch)} — {e!r}")
    _UC_SCHEMA_ENSURED = True


def get_spark():
    """Return SparkSession or None if PySpark is not available."""
    try:
        from pyspark.sql import SparkSession

        return SparkSession.builder.getOrCreate()
    except Exception:
        return None


def _rows_to_pandas(rows: Rows, columns: Sequence[str]):
    import pandas as pd

    return pd.DataFrame(list(rows), columns=list(columns))


def write_demo_table(
    table_short_name: str,
    rows: Rows,
    columns: Sequence[str],
    *,
    mode: str = "overwrite",
    spark=None,
    local_output_dir: Optional[Path] = None,
) -> str:
    """
    Write rows to Delta at ``{catalog}.{schema}.{table_short_name}`` (see `catalog_schema()`).

    Target catalog/schema default to **energy_utilities.energy_trading2** per `README.md`.

    Otherwise (no Spark) write CSV under `local_output_dir` or `modules/forecasting/_demo_output/`.

    Returns the full three-part table name or CSV path.
    """
    if not rows:
        raise ValueError(f"no rows for {table_short_name}")

    spark = spark or get_spark()
    full_name = full_table_name(table_short_name)

    pdf = _rows_to_pandas(rows, columns)

    if spark is not None:
        ensure_uc_schema(spark)
        sdf = spark.createDataFrame(pdf)
        try:
            writer = sdf.write.mode(mode).format("delta")
            if mode == "overwrite":
                writer = writer.option("overwriteSchema", "true")
            writer.saveAsTable(full_name)
            return full_name
        except Exception as e:
            if allow_csv_fallback():
                print(f"[write_demo_table] Delta save failed ({e!r}); falling back to CSV.")
            else:
                raise RuntimeError(
                    f"Delta write to {full_name} failed. Fix UC permissions or schema; "
                    f"or set DEMO_ALLOW_CSV_FALLBACK=1 to dump CSV. Original error: {e!r}"
                ) from e

    out = local_output_dir or (demo_data_dir().parent / "_demo_output")
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{table_short_name}.csv"
    pdf.to_csv(path, index=False)
    return str(path.resolve())


def write_demo_table_csv_only(
    table_short_name: str,
    rows: Rows,
    columns: Sequence[str],
    *,
    local_output_dir: Optional[Path] = None,
) -> str:
    """Write CSV without pandas (stdlib only)."""
    out = local_output_dir or (demo_data_dir().parent / "_demo_output")
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{table_short_name}.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(list(columns))
        for row in rows:
            w.writerow(["" if v is None else v for v in row])
    return str(path.resolve())


def preview(rows: Rows, columns: Sequence[str], n: int = 5) -> None:
    """Pretty-print a small sample (works in notebooks without Spark)."""
    import pandas as pd

    df = _rows_to_pandas(rows, columns)
    print(df.head(n).to_string())
    print(f"... ({len(df)} rows)")
