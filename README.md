# databricks-energy-trading

**Energy Trading** solution accelerator by Databricks — a reference architecture and demo stack for **European wholesale power and gas** trading and risk: market data, trade capture, forecasting, and strategy workflows on the Databricks Lakehouse.

## Capability overview

Functional and non-functional requirements are captured in **`modules/forecasting/features/`**. The parent brief ([`input.md`](modules/forecasting/features/input.md)) describes platform scope (e.g. coupled day-ahead auctions, intraday, REMIT/EMIR context, balancing data) and **inherited UI rules** for the bundled Databricks App. Each numbered spec adds detailed §4.x requirements and a **Demo data** block (notebook + `demo_*` Delta tables in Unity Catalog).

| # | Capability | What it covers |
|---|------------|----------------|
| **01** | [**Market data and visualisation**](modules/forecasting/features/01-market-data-and-visualisation.md) | Ingestion, cataloguing, and consumption of prices, system/TSO-style data, weather and commodity inputs, fundamentals, and internal marks — with curves, spreads, heatmaps, and **audit-grade lineage**. Demo tables include hourly spot-style prices, bronze feeds, transparency and imbalance series, gas/carbon, grid signals, and cross-border flows. |
| **02** | [**Trade capture and pricing**](modules/forecasting/features/02-trade-capture-and-pricing.md) | **Book of record** for deals: economic terms aligned with wholesale practice, REMIT-oriented fields, EMIR-style identifiers, marking and valuation hooks. Demo: OTC-style trades, consumer contracts, downstream export metadata. |
| **03** | [**Forecasting and predictive analytics**](modules/forecasting/features/03-forecasting-and-predictive-analytics.md) | **Governed** load/RES and price forecasts (including probabilistic bands), carbon/spark-style analytics, **backtest metrics**, **drift** monitoring, and regime labels — aligned to European gate timings and model-risk expectations. |
| **04** | [**Strategy, optimisation and algorithmic trading**](modules/forecasting/features/04-strategy-optimisation-and-algorithmic-trading.md) | Parameterised **strategies**, **backtests**, portfolio/scenario framing, **alert** rules and events, dashboard KPIs, TSO/market context, forecast vs actual — plus controls narrative for **shadow / automated** paths (kill switch, limits) without implying live execution in the demo. |

Together these capabilities form a single product story: **data → deals → forecasts → research and controls**.

## Demo data and Unity Catalog

Synthetic **Delta** tables are produced by notebooks **`01` → `04`** under [`modules/forecasting/notebooks/`](modules/forecasting/notebooks/). Configuration, run order, and catalog defaults are documented in [`modules/forecasting/README.md`](modules/forecasting/README.md). Typical default location: **`energy_utilities`.`energy_trading2`** (override with `DEMO_UC_*` where documented).

## Databricks App UI

The Dash app in [`app/`](app/) implements capability routes that read from the same **`demo_*`** tables via the **SQL warehouse** selected in the app header. Runtime entrypoint and bundle wiring: [`app/app.yaml`](app/app.yaml), [`app/requirements.txt`](app/requirements.txt).

## Deploy (bundle)

From the repository root, [`install.sh`](install.sh) validates and deploys the **Databricks Asset Bundle** (`databricks.yml`): demo-data **job** and **Databricks App** resource. After deploy, run the job to seed tables, then run the app resource as described in `install.sh`.

---

*For the full UI contract (copy, loading states, layout), see **UI implementation — inherited instructions** in [`modules/forecasting/features/input.md`](modules/forecasting/features/input.md).*
