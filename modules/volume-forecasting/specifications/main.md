## Volume Forecasting (Demand & Generation Volumes)

> **Domain brief** — market context, forecasting desk mechanics, and eight Databricks capabilities are in this file.  
> **Implementation** — how to turn this brief into notebooks, Unity Catalog tables, Dash routes, and bundle deploy: **[`instructions.md`](./instructions.md)**.

| Document | Role |
| --- | --- |
| **[`instructions.md`](./instructions.md)** | Repository layout, UC conventions (`volume_forecast_*`), notebooks, app pages, deploy/validate, inherited UI rules |
| **`main.md` (this file)** | Domain narrative, capabilities, and capability intent (single source of truth for *what* to build) |
| **Sub-specifications (`01`–`08`)** | Per-capability datasets, workflow, app UI, and lineage (derived from this file) |

### Specification set

Each capability has a detailed sub-spec (datasets, workflow, app UI, relationships). This file is the domain narrative; the sub-specs carry the build detail.

| # | Capability | Core question |
| --- | --- | --- |
| **01** | **[Customer Consumption — Short Term](./01-customer-consumption-short-term.md)** | How much will our retail and C&I book consume over the next hours to days, interval by interval? |
| **02** | **[Customer Consumption — Long Term](./02-customer-consumption-long-term.md)** | How much load must we serve months to years out as electrification reshapes demand? |
| **03** | **[Industry Involvement](./03-industry-involvement.md)** | How much do large industrial sites draw, and how much of that demand is flexible? |
| **04** | **[Smart Metering](./04-smart-metering.md)** | How do millions of AMI meters roll up into governed, forecast-ready load profiles? |
| **05** | **[Wind Forecasting](./05-wind-forecasting.md)** | How much will each wind asset generate per interval, and how wide is the ensemble? |
| **06** | **[Solar Forecasting](./06-solar-forecasting.md)** | How much will utility-scale and behind-the-meter PV generate, and when does midday surplus bite? |
| **07** | **[Publication & Net-Volume Reconciliation](./07-publication-net-volume.md)** | What is the single official, versioned net-volume the desks are allowed to trade on? |
| **08** | **[Forecast Accuracy & Value](./08-forecast-accuracy-value.md)** | How wrong were we, by how much in euros, and which model should be champion? |

> **04 owns the shared dimensions** (`volume_forecast_dim_zones`, `volume_forecast_dim_segments`, `volume_forecast_dim_intervals`) and the curated meter profile every consumption capability reads — build it first. **05 / 06** own their asset registries. **07** reconciles all legs into the official net volume; **08** scores it.

### Implementation quick reference (see [`instructions.md`](./instructions.md) for detail)

- **Notebooks:** `modules/volume-forecasting/notebooks/` — planned `01` → `08` (not yet wired in `energy_trading_demo_data`)
- **Overview UI:** `app/pages/volume_forecast_overview.py` — presentation deck at `/volume-forecasting/overview`
- **Capability routes (planned):** `/volume-forecasting/consumption-short-term`, `/consumption-long-term`, `/industry`, `/smart-metering`, `/wind`, `/solar`, `/publication`, `/accuracy`
- **UC target:** `energy_utilities.energy_trading2`, table prefix `volume_forecast_*` (override via `DEMO_UC_CATALOG` / `DEMO_UC_SCHEMA`)
- **Deploy:** `./install.sh`, then `databricks bundle run energy_trading_app` (data job extension TBD)

---

Volume forecasting answers **how many megawatts** the portfolio, its customers, and the grid will consume and produce — before traders square positions, before schedulers nominate, and before risk sizes hedges. It sits **upstream** of both the **long-term curve desk** (structural hedge volumes and PPA load shapes) and the **short-term prompt desk** (interval-by-interval re-forecast and squaring). Get the volume wrong and every downstream price decision inherits the error as imbalance cash-out, mis-sized hedges, or unserved load.

* **Timeframe:** Real-time and intraday (15-minute grain for European SDAC / XBID) for the prompt book; day-ahead and week-ahead for scheduling; month-, quarter-, and year-ahead for structural planning and PPAs.
* **Two sides of the balance:** **Demand** (retail, commercial, and industrial consumption) and **supply** (intermittent renewable generation — wind and solar). Net volume — demand minus must-run generation — is what the desk actually hedges and squares.
* **Regulatory duty, not just optimisation:** the supplier forecasts and nominates under **Balance Responsible Party (BRP)** obligations to the TSO. Volume forecasting is a compliance function as much as a commercial one.
* **Primary objective:** **Credible, official physical volumes** at every horizon, with an auditable handoff to the trading desks that consume them — and a euro figure on the cost of being wrong.

---

### 1. What Matters Most to the Volume Forecasting Desk

The forecasting desk is judged on accuracy and on the **trust** trading places in its numbers. The recurring concerns:

* **Horizon-appropriate drivers:** Short-term consumption is driven by weather, day-of-week, and live metering; long-term consumption is driven by macroeconomics, electrification (EVs, heat pumps), and structural efficiency gains. The same "load forecast" label hides two very different modelling problems.
* **Behind-the-meter complexity:** Rooftop solar, home batteries, and EV charging mean the meter no longer measures pure consumption. Net load (gross demand minus behind-the-meter generation) is what the grid and the desk see — and it is increasingly volatile.
* **Industrial lumpiness and flexibility:** A handful of large industrial sites can move the zonal balance more than thousands of households. Their consumption follows production schedules, shift patterns, and — crucially — **demand-side flexibility** that can be dispatched or curtailed for a price.
* **Renewable ensemble spread:** Wind and solar output depend on multiple numerical weather prediction (NWP) models. The desk needs mean, spread, and scenario tails **per asset** — not a single deterministic line — and needs them re-forecast as new weather lands. Solar additionally drives the **midday cannibalization / negative-price** regime that dominates capture-price economics.
* **Metering scale, latency, and privacy:** Millions of smart meters generate high-cardinality, late-arriving, sometimes-corrupt telemetry. Household reads are **personal data (GDPR)** — consent, anonymization, and access control are business requirements. Turning that firehose into clean, governed, forecast-ready profiles is a data-engineering and governance problem before it is a modelling problem.
* **Accuracy is money:** Forecast error flows straight to imbalance cash-out and mis-sized hedges. The desk must put a **euro value on a percentage point of error** to justify model investment and to hold itself accountable — and must publish **one official number** so traders never square on a stale or draft forecast.

---

### 2. The Volume Forecasting Data Stack

```
Volume Forecasting Data Stack
├── Smart metering: AMI interval reads, register reads, meter events, behind-the-meter PV, EV charging
├── Customer & tariff: account segments, retail vs C&I, contracted volumes, tariff & flexibility profiles
├── Industrial telemetry: site SCADA, production schedules, demand-response availability
├── Weather: NWP ensembles (ECMWF, GFS, ICON), hub-height wind, temperature, irradiance & cloud cover
├── Asset telemetry: wind & solar SCADA output, availability, curtailment, wake/soiling losses
├── Market & imbalance: imbalance / cash-out prices for costing forecast error
└── Actuals & registry: realised consumption and generation for backtesting and bias correction
```

* **Demand-side data** dominates by volume (millions of meters) and drives short- and long-term consumption forecasts.
* **Supply-side data** (wind, solar) is lower cardinality but higher volatility, and couples tightly to weather.
* **Reference & market data** (customer segments, asset registry, tariff calendars, imbalance prices) give every forecast its business context and let the desk price the cost of error.

---

### 3. Primary Objectives (Eight Capabilities)

#### Capability 01 — Customer Consumption · Short Term

Forecast retail and commercial demand from **now through the next several days** at 15-minute grain. Drivers are weather (temperature, irradiance), calendar (weekday / holiday / season), and the **latest smart-meter telemetry**. This is the load number the prompt desk squares against.

* **Trader question:** *"How much will my book consume this afternoon and tomorrow, and where is the uncertainty band?"*
* **Probabilistic output:** P10 / P50 / P90 per interval — the prompt desk squares against P50 but sizes risk against the band.
* **Databricks fit:** Structured Streaming for live meter ingest, Feature Store for weather/calendar features, MLflow for short-horizon load models; gold tables consumed by short-term squaring.
* **Handoff:** Feeds `short_term` near-delivery deviation and squaring (net position = consumption − generation − hedge).

#### Capability 02 — Customer Consumption · Long Term

Forecast structural demand **months to years out** for hedge sizing, retail book planning, and PPA load shapes. Drivers are macroeconomics, **electrification** (EV adoption, heat-pump roll-out), efficiency trends, and population/industrial growth — not next week's weather.

* **Trader question:** *"What annual and seasonal load shape do we hedge for Cal+1 through Cal+3, and how does electrification bend the curve?"*
* **Probabilistic output:** P50 with P75 / P90 scenario layers so the curve desk can hedge to the same P-levels it uses on the layered hedge matrix.
* **Databricks fit:** Distributed Spark scenario simulation, MLflow for assumption tracking (EV penetration, heat-pump uptake), Delta time-travel to audit how a forecast vintage was produced.
* **Handoff:** Feeds the **long-term curve desk** load shapes and the PPA / cannibalization models.

#### Capability 03 — Industry Involvement

Model large **industrial and C&I** consumption as a first-class segment: site-level demand tied to production schedules and shift patterns, plus **demand-side flexibility** (load that can shift, shed, or boost for a price). A few sites can swing the zonal balance materially.

* **Trader question:** *"Which industrial sites are drawing, what is their baseline, and how much flexible MW can I count on for balancing?"*
* **Databricks fit:** Lakeflow ingest of site SCADA and production plans, ML baselining of expected vs flexible load, governed views shared with the short-term DSR / market-access desk.
* **Handoff:** Industrial flexibility feeds short-term DSR aggregation; industrial baseline feeds both short- and long-term consumption totals.

#### Capability 04 — Smart Metering

The **data-engineering backbone**: ingest millions of AMI interval reads, handle late and corrupt records, deduct behind-the-meter PV, and roll meters up into governed **load profiles** by segment, tariff, and zone. Every consumption forecast (01, 02, 03) reads from these curated profiles.

* **Trader question:** *"Can I trust the load profile feeding my forecast — is it complete, clean, and current?"*
* **Governance & privacy:** household reads are personal data — apply **Unity Catalog** access controls, row/column masking, and consent-aware aggregation so individual meters are never exposed downstream.
* **Databricks fit:** Auto Loader / Structured Streaming for high-cardinality ingest, Lakeflow Declarative Pipelines for bronze → silver → gold profiling, Unity Catalog for governance and lineage, Lakehouse Monitoring for data-quality SLAs.
* **Handoff:** Curated `volume_forecast_*` profile tables are the **shared input** to capabilities 01–03.

#### Capability 05 — Wind Forecasting

Forecast **wind generation per asset** at 15-minute grain by blending NWP ensembles with SCADA bias correction and availability. The desk needs mean output, ensemble spread (P10/P90), and per-asset deviation — re-forecast as new weather lands.

* **Trader question:** *"How much will each wind farm generate this interval, and how confident am I?"*
* **Databricks fit:** Weather Delta tables (optionally via Marketplace / Delta Share), Feature Store for hub-height features, MLflow champion/challenger per asset class; gold ensemble tables consumed by squaring and net-position views.
* **Handoff:** Latest published wind forecast per asset feeds short-term squaring and long-term renewable hedge volumes.

#### Capability 06 — Solar Forecasting

Forecast **solar PV generation** — both the 200 MW utility-scale plant and aggregated **behind-the-meter rooftop PV** — at 15-minute grain from irradiance and cloud-cover NWP plus satellite nowcasting and SCADA. Solar is the engine of the **midday surplus** that drives negative prices and capture-price cannibalization.

* **Trader question:** *"How much solar floods the grid at midday, and how far does it push prices (and my capture value) down?"*
* **Probabilistic output:** P10 / P50 / P90 per asset; clear-sky vs actual deltas to flag cloud-driven ramps.
* **Databricks fit:** Irradiance/satellite Delta tables (Marketplace / Delta Share), Feature Store for clear-sky + soiling features, MLflow champion/challenger; gold ensemble feeds net-volume and capture-price models.
* **Handoff:** Feeds short-term squaring (midday long position) and the long-term **capture-price / PPA cannibalization** view; behind-the-meter PV nets against consumption in capability 04.

#### Capability 07 — Publication & Net-Volume Reconciliation

Blend demand (01, 02, 03) and generation (05, 06) into **one official, versioned net-volume as-of** that trading is allowed to consume. Draft model runs must never reach squaring or nominations. This capability owns the **single source of truth** and its audit trail.

* **Trader question:** *"What is the official net position right now, which forecast vintage is it, and what changed since the last publish?"*
* **Output:** `publication_status` ∈ {`DRAFT`, `PUBLISHED`, `SUPERSEDED`}, `as_of_ts`, version, and a per-consumer handoff (`SHORT_TERM`, `LONG_TERM`, `DSR`, `CONTROL_TOWER`).
* **Databricks fit:** Delta versioning + time-travel for audit, Unity Catalog governed gold publish, audit columns; supersede-on-republish pattern.
* **Handoff:** The **only** table the trading desks read for net volume — everything upstream is internal.

#### Capability 08 — Forecast Accuracy & Value

Score **published** forecasts against realised actuals and — critically — translate error into **euros**. MAE / RMSE / bias by horizon, asset, and segment; model drift; champion/challenger; and **cost of error** = forecast deviation × imbalance/cash-out price. This is the desk's KPI and its business case.

* **Trader question:** *"How wrong were we last week, what did it cost in imbalance, and is a challenger model worth promoting?"*
* **Output:** accuracy rollups by `lead_bucket` / asset / segment, drift alerts, and a **value-of-accuracy** view in € (imbalance avoided / incurred).
* **Databricks fit:** Lakehouse Monitoring for drift, MLflow for champion/challenger metrics, Delta gold rollups, alerting.
* **Handoff:** Feeds model governance (which version is champion) and a management view of forecasting's commercial impact.

#### Scope notes (candidate extensions, not yet in scope)

* **Gas demand forecasting:** this module is **power-only**. Heating-driven gas demand and gas-for-power burn are natural extensions if the demo expands to the gas book.
* **EV & residential flexibility:** EV smart-charging, vehicle-to-grid, and heat pumps appear here as demand **drivers** (02) and an emerging **short-term flexible segment** — a residential analogue to industrial DSR (03). Model as an explicit flexibility band once smart-meter penetration supports it.

---

### 4. Cross-Desk Handoff (same 1,000 MW portfolio)

Volume forecasting does **not** set prices — it sets the **physical volumes** every price-sensitive decision depends on. The portfolio context is the same Central-European (EEX/DE hub) book used across the modules: 500 MW flexible CCGT, 300 MW onshore wind, 200 MW utility-scale solar, plus the retail and C&I load behind it. Trading consumes the **published** net volume (07) — never the raw capability outputs.

| Downstream desk | Consumes from volume forecasting |
| --- | --- |
| **Short-term squaring** | Published net volume (07) per interval — short-term consumption (01), wind (05), solar (06), industrial flexibility (03) |
| **Long-term curve / origination** | Structural load shapes (02) and renewable volume profiles (05, 06) for hedge sizing and PPA capture-price / cannibalization models |
| **Short-term DSR & market access** | Industrial demand-side flexibility (03) for bid-stack aggregation |
| **Control tower** | Official as-of net-volume headline (07) and severe-deviation context (08) for shift operations |
| **Risk & management** | Forecast accuracy and cost-of-error (08) for model governance and commercial reporting |

Net position the desks act on (published via capability 07):

$$\text{Net Volume}_{interval} = \text{Consumption}_{01,02,03} - \text{Generation}_{05,06} - \text{Contracted Hedge}$$

---

### 5. Key Forecasting Challenges (and why a lakehouse helps)

* **Two horizons, one platform:** Short-term (weather/telemetry-driven) and long-term (macro/electrification-driven) forecasts share customer and metering inputs but need different models. A single governed lakehouse lets both read the same curated profiles without copying data.
* **Cardinality vs. volatility:** Smart metering is a high-cardinality ingest problem; wind and solar are high-volatility modelling problems. Spark + Auto Loader handles the former; MLflow + ensemble features handle the latter.
* **Behind-the-meter erosion:** Rooftop PV and EVs make the meter an unreliable measure of consumption. Deducting behind-the-meter generation in the smart-metering layer (04) and forecasting it explicitly (06) keeps every downstream forecast honest.
* **One official number:** Five forecast streams must reconcile into a single published, versioned net volume (07). Delta versioning and Unity Catalog give traders a governed source of truth with a full audit trail — no spreadsheets, no stale drafts.
* **Accuracy you can price:** Auditability (Delta time-travel + MLflow) lets risk reproduce any forecast vintage, and the cost-of-error view (08) turns "we improved MAE by 2%" into "we avoided €X of imbalance" — the language the business funds.

---

### Summary Table: Tech Stack Mapping

| # | Capability | Core forecasting problem | Databricks components to highlight |
| --- | --- | --- | --- |
| **01** | **Customer Consumption · Short Term** | Live, weather-driven load at 15-min grain | Structured Streaming, Feature Store, MLflow, Delta gold |
| **02** | **Customer Consumption · Long Term** | Structural demand & electrification scenarios | Spark distributed compute, MLflow assumption tracking, Delta time-travel |
| **03** | **Industry Involvement** | Industrial baseline + demand-side flexibility | Lakeflow pipelines, ML baselining, Unity Catalog governed shares |
| **04** | **Smart Metering** | High-cardinality ingest → governed, private profiles | Auto Loader, Lakeflow Declarative Pipelines, Unity Catalog (masking/RLS), Lakehouse Monitoring |
| **05** | **Wind Forecasting** | Per-asset ensemble generation forecast | Weather Delta / Marketplace, Feature Store, MLflow champion/challenger |
| **06** | **Solar Forecasting** | Midday surplus & capture-price cannibalization | Irradiance/satellite Delta / Marketplace, Feature Store, MLflow |
| **07** | **Publication & Net-Volume Reconciliation** | One official, versioned net volume for trading | Delta versioning + time-travel, Unity Catalog governed publish |
| **08** | **Forecast Accuracy & Value** | Error in euros + model governance | Lakehouse Monitoring, MLflow metrics, Delta rollups, alerting |

---

*Implementation conventions for notebooks, tables, and app pages live in [`instructions.md`](./instructions.md). Parent brief for the prompt desk that consumes these volumes: [`../short-term/specifications/main.md`](../short-term/specifications/main.md). All data is **synthetic** and illustrative — not a substitute for exchange, TSO, or vendor forecast feeds.*
