# Forecasting and predictive analytics — specification (Europe)

**Parent brief:** [input.md](./input.md)

## Demo data (notebook and tables)

Synthetic demo for this capability is created by [**`03_forecasting_and_predictive_analytics.ipynb`**](../notebooks/03_forecasting_and_predictive_analytics.ipynb) (run as **3 of 4** in the sequence in [`README.md`](../README.md)). It materialises **Delta** tables in Unity Catalog under the default location **`energy_utilities`.`energy_trading2`** (override with `DEMO_UC_*` env vars in [`demo_data/notebook_helpers.py`](../demo_data/notebook_helpers.py)). Use these tables when wiring the [Databricks App](../../../app/) to catalogued data instead of local-only synthetic helpers.

**UI (inherited):** When implementing widgets for this capability, follow [UI implementation — inherited instructions](./input.md#ui-inherited-instructions) in `input.md`—use a **consistent theme** with the rest of the app, bind widgets **explicitly** to this notebook and the `demo_*` tables below, and write **titles, tooltips, and footnotes** that describe the capability and the meaning of the demo columns (not generic chart labels).

| Delta table | Description (demo) |
|-------------|-------------------|
| `demo_forecasts_load_gen` | Load / renewables forecasts by zone and model |
| `demo_forecasts_market_prices` | Price forecasts with quantiles and imbalance risk index |
| `demo_carbon_spark_daily` | Carbon / spark-style daily analytics |
| `demo_backtest_metrics` | Backtest skill metrics (MAE, RMSE, pinball, etc.) |
| `demo_drift_metrics` | Feature drift (PSI-style) by model and zone |
| `demo_regime_labels` | Regime / structural-break labels (metadata) |

## 1. Purpose

Deliver forecasts and models aligned to **European market timing**: day-ahead gate closure, continuous intraday trading, imbalance settlement periods (often **15-minute** products in Germany and neighbouring areas), and longer hedging horizons. Use statistical and machine-learning methods only where **governed data** and **model risk** processes support them; benchmark against simple baselines and against **purchased vendor forecasts** where the organisation subscribes to them.

Forecasts do not guarantee trading outcomes; model risk and human judgement remain explicit.

## 2. Scope

| In scope | Out of scope |
|----------|----------------|
| Models on governed internal and licensed external data | Selling forecasts as a regulated service without a separate approval process |
| Probabilistic outputs (quantiles, scenarios) where decisions need ranges | Real-time plant control (SCADA) |
| Point-in-time feature pipelines for backtests and research | Official TSO scheduling submissions (unless owned by another system) |

**Horizons:** D+1 auction-relevant, same-day intraday, imbalance window, weeks to seasons for origination and treasury-style hedging.

## 3. Stakeholders

- Short-term traders (DA, ID, imbalance).
- Origination and structuring (medium-term views).
- Quantitative analysis and data science.
- Risk (stress and scenario consumption).
- Operations (nominations support—read-only forecasts unless otherwise agreed).

## 4. Functional requirements

### 4.1 Fundamentals forecasting

- **Load:** zone total load (and sub-regions if metering exists); exogenous drivers include temperature, calendar (holidays, day-of-week), daylight where relevant.
- **Renewables:** wind and solar generation forecasts using **NWP** inputs (e.g. ECMWF, DWD ICON, commercial blends) and asset metadata (capacity, location, technology); respect public **availability times** of weather model runs.
- **Uncertainty:** quantiles or scenarios for wind and solar where risk or trading needs bands; curtailment and redispatch only as features if data is available in time for decision cut-offs.
- **Thermal / hydro:** availability factors or hydrology where the portfolio requires—scope per asset list.

### 4.2 Price and spread forecasting

- **Targets:** zone prices (DA, ID), cross-border spreads, imbalance prices or premia vs DA, gas hub spreads—defined per desk charter.
- **Features must respect real cut-offs:**
  - **Before DA gate:** latest fundamentals, interconnector nominations where published, renewable forecast error history.
  - **Intraday:** residual load proxies, updated renewable nowcasts, order-flow proxies only if data is licensed.
  - **Imbalance:** TSO data available before the relevant bid deadline; system imbalance direction history where published.
- **Ensembling:** blend statistical, ML, and forward-implied anchors with documented weights and rebalancing rules.

### 4.3 Benchmarking and evaluation

- **Baselines:** persistence, seasonal naive, simple AR/ridge; vendor forecasts side-by-side if purchased.
- **Metrics:** MAE/RMSE for point forecasts; pinball loss or CRPS for distributional forecasts; avoid relying on MAPE alone when prices approach zero.
- **No leakage:** walk-forward or rolling-origin validation; features joined with timestamp not after decision time.
- **Structural breaks:** document known regime changes (fuel shocks, policy, interconnector commissioning); do not assume stationarity without evidence.

### 4.4 MLOps and governance

- **Registry:** model version, code commit, training data snapshot id, owner, approval for production promotion.
- **Runs:** scheduled inference with alerts on failure; idempotent outputs per run id.
- **Monitoring:** input drift and output distribution shift vs training window; manual review triggers.
- **Explainability:** feature importance or SHAP for selected models; limitations stated for front-office use (not investment advice).

## 5. Non-functional requirements

- **Reproducibility:** same model version and data snapshot yields the same outputs within floating-point tolerance.
- **Cut-off SLA:** forecasts published before documented deadlines relative to market gates (e.g. before DA order submission where that is the use case).
- **Cost:** training budgets and shared feature materialisation to avoid duplicate compute.

## 6. Interfaces

- **Input:** curated tables from market data (prices, TSO, weather); reference data (zones, assets).
- **Output:** versioned forecast tables; API or SQL for dashboards and downstream systems; MLflow (or equivalent) for experiments and registry.

## 7. Success criteria

- Documented out-of-sample performance vs agreed baselines before production promotion.
- Cut-off compliance measured against a published schedule (targets agreed with operations—not fixed percentages in this spec).
- Independent replay of a forecast run given registry metadata and frozen inputs.

## 8. Open points

- Weather licences may restrict storage duration and derived features—legal review required.
- Human override of model output—policy and logging agreed with risk.
