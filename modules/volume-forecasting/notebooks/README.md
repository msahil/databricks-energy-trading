# Volume forecasting notebooks

Seed notebooks that materialise the `volume_forecast_*` Delta tables in `energy_utilities.energy_trading2`.
Each notebook reads `catalog` / `schema` from widgets (or `DEMO_UC_CATALOG` / `DEMO_UC_SCHEMA`) and applies
Unity Catalog comments from [`uc_table_comments.py`](./uc_table_comments.py) in its final cell.

| Notebook | Capability | Depends on |
|---|---|---|
| `04_smart_metering.ipynb` | 04 — Smart Metering (owns shared dims + curated meter profile) | — |
| `01_consumption_short_term.ipynb` | 01 — Customer Consumption · Short Term | 04 |
| `02_consumption_long_term.ipynb` | 02 — Customer Consumption · Long Term | 04 |
| `03_industry_involvement.ipynb` | 03 — Industry Involvement | — |
| `05_wind_forecasting.ipynb` | 05 — Wind Forecasting (owns wind asset registry) | — |
| `06_solar_forecasting.ipynb` | 06 — Solar Forecasting (owns solar asset registry; BTM reconciliation) | 04 |
| `07_publication_net_volume.ipynb` | 07 — Publication & Net-Volume Reconciliation (source of truth) | 01, 03, 05, 06 |
| `08_forecast_accuracy_value.ipynb` | 08 — Forecast Accuracy & Value (error → euros) | 07 |

Supporting files:

- `uc_table_comments.py` — `COMMENT ON TABLE` / `COLUMN` metadata for coding agents and Genie, plus
  per-notebook `apply_volume_forecast_notebook_0X_comments()` helpers.

**Run order:** `04 → (01, 02, 03) + (05, 06) → 07 → 08` after the demo schema reset notebook.
The bundle job [`resources/energy_trading_demo_data_job.yml`](../../../resources/energy_trading_demo_data_job.yml)
wires this dependency graph on serverless compute.
