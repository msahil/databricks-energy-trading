# databricks-energy-trading

European energy trading demo on the Databricks lakehouse — two complementary modules with governed Unity Catalog gold tables, interactive Dash capability pages, presentation overviews, and Genie spaces for natural-language desk questions.

**Unity Catalog target:** `energy_utilities.energy_trading2` (`short_term_*` and `volume_forecast_*` tables).

## What’s in the demo

### Short-term trading

Prompt-desk workflows for squaring renewable delta before gate close, running the physical book 24/7, and monetising aggregated flex.

| Capability | Route | What it shows |
|---|---|---|
| Overview & Architecture | `/short-term/overview` | Slide deck — end-to-end prompt-desk story |
| Trading near delivery | `/short-term/near-delivery` | Net position, forecast deviations, squaring actions, imbalance cash-out, backtest |
| Control Tower | `/short-term/control-tower` | Balance ribbon, asset dispatch, grid/gates, REMIT feed, trading copilot, shift handover |
| DSR & Market Access | `/short-term/dsr` | Fleet availability, bid stack, dispatch verification, owner settlement |
| Trader insights (Genie) | `/short-term/insights` | Genie launcher over short-term gold tables and metric views |

Specifications: [`modules/short-term/`](modules/short-term/) · Notebooks: [`modules/short-term/notebooks/`](modules/short-term/notebooks/)

### Volume forecasting

Forecasting desk workflows — meter-grounded demand, renewables supply, official net volume publication, and accuracy priced in euros.

| Capability | Route | What it shows |
|---|---|---|
| Overview & Architecture | `/volume-forecasting/overview` | Slide deck — volumes before prices move |
| Customer Consumption (ST) | `/volume-forecasting/consumption-short-term` | Weather-driven probabilistic load (P10/P50/P90), segments, forecast move |
| Customer Consumption (LT) | `/volume-forecasting/consumption-long-term` | Multi-year scenarios, seasonal shape, electrification drivers |
| Industry Involvement | `/volume-forecasting/industry` | Large-site baseline, flexibility envelope, site registry |
| Smart Metering | `/volume-forecasting/smart-metering` | AMI feed health, BTM PV deduction, curated net-load profiles |
| Wind Forecasting | `/volume-forecasting/wind` | NWP ensemble fan, asset breakdown, curtailment risk, forecast move |
| Solar Forecasting | `/volume-forecasting/solar` | Irradiance fan, utility-scale supply, BTM reconciliation |
| Publication & Net Volume | `/volume-forecasting/publication` | Official reconciled net volume, leg stack, revisions, consumer handoff |
| Forecast Accuracy & Value | `/volume-forecasting/accuracy` | MAE by leg, lead-time curve, champion/challenger, cash-out cost, drift |
| Renewables insights (Genie) | `/volume-forecasting/insights` | Genie launcher over renewables and publication tables |

Specifications: [`modules/volume-forecasting/`](modules/volume-forecasting/) · Notebooks: [`modules/volume-forecasting/notebooks/`](modules/volume-forecasting/notebooks/)

### Landing page

`/` — executive capability overview (no navigation links; use the sidebar).

Each capability page includes a **Presenter guide** (pain point → business value → widget walkthrough) for demo delivery.

### Suggested demo flows

- **Short-term:** Near delivery → Control Tower → DSR → Trader insights (Genie)
- **Renewables / volume:** Wind → Solar → Publication → Accuracy → Renewables insights (Genie)
- **Full story:** Volume forecasting (demand + supply + publish) → Short-term squaring on the published net volume

---

## Prerequisites

- Databricks CLI authenticated to your workspace (`databricks auth login`)
- SQL warehouse with access to `energy_utilities.energy_trading2`
- Bundle deploy permissions for jobs and Databricks Apps
- For Genie pages: demo job must complete notebook `04_trader_insights_genie` (short-term) and `09_renewables_insights_genie` (volume forecasting)

---

## Setup and deploy

From the repository root:

```bash
./install.sh
```

This validates and deploys the bundle (`energy_trading_demo_data` job + `energy_trading_app`).

Then materialise demo data and publish the app:

```bash
# Drops and recreates the schema, runs all short-term + volume-forecasting notebooks (serverless)
databricks bundle run energy_trading_demo_data

# Deploy / update the Databricks App
databricks bundle run energy_trading_app
```

Open the app from **Workspace → Apps**, or use the URL printed after `bundle run`.

The demo data job **drops and recreates** `energy_utilities.energy_trading2` on every run so each execution starts fresh.

Override catalog/schema via job parameters or app env vars (`DEMO_UC_CATALOG`, `DEMO_UC_SCHEMA` in [`app/app.yaml`](app/app.yaml)).

---

## Using the app

1. Run `energy_trading_demo_data` at least once so gold tables exist.
2. Open the app and **select a running SQL warehouse** in the header — all capability pages query Unity Catalog through Statement Execution.
3. Navigate via the sidebar: **Overview → Home**, then **Short Term Trading** or **Volume Forecasting**.
4. On each capability page, use toolbar filters and **Refresh** to load data (manual refresh; no auto-poll).
5. For Genie pages, pick the provisioned space, use sample question tiles, then **Open in workspace** for live Q&A.

Production runtime sets `DASH_DEBUG=false` in [`app/app.yaml`](app/app.yaml) (no Dash debug UI or hot reload).

---

## Local development

```bash
cd app
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open [http://127.0.0.1:8050/](http://127.0.0.1:8050/).

Local dev enables Dash debug mode and hot reload by default. Disable with:

```bash
DASH_DEBUG=false python app.py
```

For local UC queries, configure Databricks credentials and ensure the header warehouse selector can reach your workspace SQL warehouses. Catalog/schema default to `energy_utilities` / `energy_trading2` (same as deployed app).

---

## Repository layout

| Path | Purpose |
|---|---|
| [`app/`](app/) | Dash app — pages, shared UI, UC SQL helpers, slide decks |
| [`app/pages/`](app/pages/) | One module per capability route |
| [`app/app.yaml`](app/app.yaml) | Databricks App runtime (command, env vars) |
| [`resources/`](resources/) | Bundle job and app definitions |
| [`modules/short-term/`](modules/short-term/) | Short-term specs and seed notebooks |
| [`modules/volume-forecasting/`](modules/volume-forecasting/) | Volume forecasting specs and seed notebooks |
| [`modules/setup/`](modules/setup/) | Schema reset notebook |
| [`databricks.yml`](databricks.yml) | Root DAB configuration |

**App plumbing:** [`app/uc_sql.py`](app/uc_sql.py) (Statement Execution API) · [`app/uc_pages.py`](app/uc_pages.py) (shared page helpers, presenter modals) · [`app/shared_ui.py`](app/shared_ui.py) (sidebar navigation)
