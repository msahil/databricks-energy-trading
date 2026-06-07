## Short-Term Trading (The Prompt & Spot)

> **Domain brief** — market context, desk mechanics, and three Databricks capabilities are in this file.  
> **Implementation** — how to turn this brief into notebooks, Unity Catalog tables, Dash routes, and bundle deploy: **[`instructions.md`](./instructions.md)**.

| Document | Role |
| --- | --- |
| **[`instructions.md`](./instructions.md)** | Repository layout, UC conventions (`short_term_*`), streaming notebooks, app pages, deploy/validate, inherited UI rules |
| **`main.md` (this file)** | Domain narrative and capability intent (single source of truth for *what* to build) |
| **Sub-specifications** | Per-capability schemas, widgets, and lineage (derived from this file) |

### Specification set

| # | Capability | Sub-specification |
| --- | --- | --- |
| **01** | **Trading near delivery** | [`01-trading-near-delivery.md`](./01-trading-near-delivery.md) |
| **02** | **24/7 Operations & Live Dispatch** (control tower) | [`02-operations-live-dispatch.md`](./02-operations-live-dispatch.md) |
| **03** | **DSR & Market Access** | [`03-dsr-market-access.md`](./03-dsr-market-access.md) |
| **04** | **Trader insights (Genie)** | [`04-trader-insights-genie.md`](./04-trader-insights-genie.md) |

### Implementation quick reference

- **Notebooks:** `modules/short-term/notebooks/` — [`01_trading_near_delivery.ipynb`](../notebooks/01_trading_near_delivery.ipynb), [`03_dsr_market_access.ipynb`](../notebooks/03_dsr_market_access.ipynb), [`02_operations_live_dispatch.ipynb`](../notebooks/02_operations_live_dispatch.ipynb), [`04_trader_insights_genie.ipynb`](../notebooks/04_trader_insights_genie.ipynb). Wired in job `energy_trading_demo_data` as `reset → st01 → st03 → st02 → st04` (02 aggregates 01 + 03, so it runs before Genie provisioning)
- **Overview UI:** `app/pages/short_term_overview.py` — presentation deck at `/short-term/overview`
- **Capability routes:** `/short-term/near-delivery` ([`short_term_near_delivery.py`](../../../app/pages/short_term_near_delivery.py)), `/short-term/control-tower` ([`short_term_control_tower.py`](../../../app/pages/short_term_control_tower.py)), `/short-term/dsr` ([`short_term_dsr.py`](../../../app/pages/short_term_dsr.py)), `/short-term/insights` ([`short_term_insights.py`](../../../app/pages/short_term_insights.py))
- **Genie / NL scope:** notebook 04 + `/short-term/insights` launcher (mirrors long-term). The **in-dash trading copilot** on the control tower (`short_term_gold_copilot_recommendations`) remains curated decision support; Genie covers ad-hoc cross-table questions.
- **UC target:** `energy_utilities.energy_trading2`, table prefix `short_term_` (override via `DEMO_UC_CATALOG` / `DEMO_UC_SCHEMA`)
- **Deploy:** `./install.sh`, then `databricks bundle run energy_trading_demo_data` and `energy_trading_app`

---

Short-term trading is all about the immediate physical reality of the grid. It deals with balancing supply and demand in real-time or near-real-time.

* **Timeframe:** From Week-Ahead down to Day-Ahead (DA), Intraday (ID), and real-time Balancing Markets (minutes before delivery).
* **Key Products:** Baseload/Peak Day-Ahead contracts, hourly/quarter-hourly intraday blocks, and ancillary services (balancing / control energy — aFRR, mFRR).
* **Primary Objective:** **Asset Optimization and Physical Balancing.** Trading desks (like Axpo) use the spot market to optimize physical assets—adjusting hydro dispatch, ramping a gas peaker, charging or discharging a battery, or dispatching aggregated demand-side flexibility to manage sudden renewable swings. It is also where traders exploit quick arbitrage opportunities caused by grid volatility.
* **Market Drivers:** Highly sensitive to immediate variables: 24 to 48-hour weather forecasts (wind speed, solar irradiance, temperature spikes), sudden power plant outages, interconnector failures, and localized grid congestion.

On a short-term energy trading desk—colloquially known as the **"Prompt and Spot Desk"**—the time horizon collapses from years into days, hours, and minutes. If long-term trading is a game of chess played with macroeconomic fundamentals, short-term trading is high-frequency algorithmic warfare.

Traders on this desk manage the physical reality of the grid. Their world operates on strict delivery deadlines where an incorrect calculation could mean destabilizing the power grid or incurring catastrophic imbalance penalties.

---

### 1. What Matters Most to Short-Term Traders

In the short-term window, physical execution, timing, and grid mechanics rule the desk.

* **15-Minute Structural Granularity:** With the integration of European markets under the Single Day-Ahead Coupling (SDAC), the Day-Ahead (DA) market operates on 15-minute trading intervals. Traders must manage a highly volatile **"sawtooth" price pattern** where prices experience sharp jumps between consecutive 15-minute blocks within a single hour, driven by ramping mismatches.
* **Negative Pricing Mitigation:** With massive solar oversupplies and inflexible baseload generation causing hundreds of negative-price hours annually across major European hubs (such as Germany, France, Spain, and the Netherlands), short-term traders must react rapidly. They need to know exactly when to curtail renewable assets, charge batteries, or activate demand-side response to avoid paying the market to take their power.
* **Imbalance and Cash-Out Risk:** If a trading house promises to deliver 100 MW of power in a specific 15-minute window but delivers only 80 MW due to a sudden cloud cover drop, they are "short." The Transmission System Operator (TSO) will fill that gap using expensive balancing reserves and charge the trader an **imbalance cash-out price**. Avoiding these penalizing cash-out rates is a constant priority.
* **Cross-Border Intraday Gate Closures:** Traders monitor interconnector capacities continuously. In the European Cross-Border Intraday (SIDC/XBID) market, capitalizing on regional price disparities requires executing trades before the cross-border gates close (often 15 to 30 minutes before physical delivery).

---

### 2. The Short-Term Data Stack: High-Frequency Analytics

Short-term traders require a real-time, programmatic data stack. Manual spreadsheets are insufficient; trading desks function similarly to quantitative hedge funds, deploying automated algorithmic engines fed by continuous data pipelines.

```
Short-Term Trading Data Stack
├── Weather Telemetry: Satellite Imaging, Localized Cloud Vectors, Wind-Shear Models
├── Grid Infrastructure: Real-time REMIT Outages, Interconnector Nominations
├── High-Frequency Flows: TSO System Balance (FRR/aFRR), Live Order-Book Depth
├── Asset Operations: SCADA Feed, Battery SoC (State of Charge), Thermal Ramp Rates
└── Distributed Flexibility: Submeter Telemetry, DSR Baselines, VPP Asset Registry
```

* **High-Resolution, Multi-Model Weather Ingestion:** Desks ingest immediate data feeds from major meteorological providers (ECMWF, GFS, and private weather vendors). They track real-time satellite imagery, cloud motion vectors, and localized wind-shear models to predict renewable generation shifts over the next 1 to 48 hours.
* **Real-Time Grid and Plant Telemetry (REMIT):** Traders track REMIT (Regulation on Wholesale Energy Market Integrity and Transparency) urgent market messages continuously. A sudden 1,000 MW nuclear trip in France or an unexpected outage on a subsea interconnector alters regional supply stacks within seconds.
* **The "Distributed Blindspot" Challenge:** A significant portion of European solar is distributed capacity (rooftop residential solar). Because these installations lack direct utility-scale telemetry, traders rely on advanced machine learning algorithms to deduce "behind-the-meter" generation by analyzing residual net load data from distribution grids.
* **Order Book Depth and TSO Balancing Signals:** Traders monitor the physical liquidity of exchange order books (e.g., EPEX SPOT, Nord Pool) alongside TSO balancing screens. Tracking the actual direction of the system imbalance (whether the grid is structurally short or long on energy) informs whether to buy or sell in the final minutes of intraday trading.
* **Distributed Flexibility Telemetry:** As DSR portfolios and virtual power plants (VPPs) scale, desks ingest high-cardinality submeter feeds from thousands of small assets — industrial loads, EV charging, heat pumps, and behind-the-meter batteries — to measure real-time available flexibility against contracted baselines.

---

### 3. Primary Objectives of Short-Term Trading

The prompt desk operates under three clear operational mandates that map directly to the three capabilities in this module:

* **Trade Near Delivery (Squaring & Arbitrage):** Close out the physical delta between long-term forward commitments and actual day-ahead/intraday reality. The desk clears excess volume or buys back missing capacity to enter each delivery interval balanced, and exploits the spread between the Day-Ahead auction and the continuous Intraday market before cross-border gates close.
* **Operate & Dispatch 24/7:** Run the physical portfolio in real time from a single operations view. Co-optimize flexible assets — batteries, hydro, gas peakers — across Intraday, Day-Ahead, and TSO balancing markets (aFRR/mFRR), while monitoring net imbalance, grid frequency, and REMIT events around the clock with disciplined shift handovers.
* **Aggregate Flexibility & Provide Market Access:** Pool distributed demand-side response and third-party assets into a tradable virtual power plant, prequalify it for wholesale and balancing markets, dispatch it against price and grid signals, and settle the value back to asset owners.

---

### 4. Key Short-Term Market Drivers

The forces that move the prompt and spot price curves on a minute-by-minute basis include:

* **Meteorological Shocks & Intraday Forecast Errors:** A sudden wind drop or a localized storm front that disrupts solar irradiance across central hubs will instantly spike short-term prices. Conversely, an unexpected breeze in a heavily supplied solar hour can crash prices deeply into negative territory.
* **Physical Grid Congestion and Redispatch:** Cross-border flows are limited by physical lines. If the transmission grid between northern generation zones (high wind) and southern load centers becomes heavily congested, TSOs will initiate local redispatch measures, creating significant localized price decoupling between bidding zones.
* **The Velocity of Algorithmic Execution:** Human traders cannot analyze 15-minute price steps across multiple cross-border zones simultaneously. Short-term markets are heavily driven by **automated bidding algorithms**. If multiple market algorithms trigger automated stop-losses or execution loops simultaneously due to a sudden outage, intraday prices can experience extreme, volatile price swings within seconds.
* **The State of Charge (SoC) Constraints:** The rapid build-out of utility-scale batteries across Europe means that short-term price discovery is highly dependent on battery state-of-charge limits. When battery fleets across a region hit full charge during a midday solar glut and are forced to stop absorbing power, it can trigger sharp, sudden price collapses in the intraday market.

In the short-term (Prompt & Spot) arena, data processing shifts from multi-year fundamental modeling to **sub-second streaming analytics**. Because trades are finalized in 15-minute intervals and continuous intraday gates close minutes before delivery, latency equals financial loss.

Databricks serves as an ideal environment for prompt desks because its unified intelligence platform can handle high-velocity streaming data (IoT SCADA feeds, high-frequency order books, satellite weather telemetry, distributed submeters) and serve real-time machine learning inference at scale.

---

## The Operating Day: A Concrete Portfolio

To ground the three capabilities, we follow the same **1,000 MW diversified Central Europe portfolio (EEX/DE hub)** that the long-term desk hedged on the curve — now handed to the prompt desk for physical delivery.

### The Portfolio Profile

* **Thermal:** 500 MW flexible CCGT (gas-fired, 55% efficiency, fast start-stop).
* **Intermittent Renewables:** 300 MW onshore wind + 200 MW utility-scale solar PV.
* **Flexibility Assets:** 1 × 100 MW / 200 MWh grid battery; a **150 MW aggregated DSR / VPP portfolio** of ~4,000 distributed assets (industrial loads, EV depots, heat pumps, behind-the-meter batteries).
* **The Handover:** The curve desk enters delivery hedged to ~P50. The prompt desk inherits the residual **volume risk** (will the wind actually blow?) and **profile risk** (solar lands in the cheapest hours) and must square, dispatch, and monetize flexibility interval-by-interval.

### The Operating Loop (per 15-minute interval)

1. **Re-forecast** generation as weather updates land (wind/solar by zone).
2. **Square** the net long/short delta on the continuous Intraday market before the gate closes.
3. **Dispatch** flexible assets (battery, CCGT, DSR) to the highest-value market — Intraday, Day-Ahead, or TSO balancing.
4. **Monitor** net imbalance and projected cash-out; react to REMIT events and grid-frequency signals.
5. **Settle** flexibility value back to internal P&L and external asset owners.

This loop is exactly what the three capabilities below operationalize: **(01)** squares near delivery, **(02)** runs the 24/7 control tower over dispatch and risk, and **(03)** turns distributed flexibility into a tradable, settle-able product.

---

## Capability 1: Trading Near Delivery

As wind speeds and cloud vectors shift through the day, 15-minute generation forecasts for the renewable fleet must be re-calculated continuously, and the physical long/short delta squared on the continuous Intraday (SIDC/XBID) market **before the cross-border gate closes**. This capability also tracks live imbalance exposure so the desk enters each delivery interval balanced and avoids penalizing TSO cash-out.

* **The Databricks Fit:** Structured Streaming (with ultra-low-latency Real-Time Mode) + Lakeflow Declarative Pipelines (DLT) + Multi-Stream Temporal Joins + Delta time-travel & MLflow (strategy backtesting).
* **What the desk does:**
  * **Ingestion:** Stream high-frequency weather APIs, radar/satellite imagery, and live wind/solar SCADA telemetry into a streaming pipeline; join against the long-term hedge position to derive the live residual delta.
  * **Re-forecast & square:** Continuously cleanse and aggregate telemetry, feed pre-trained ML models to produce an updated 15-minute generation profile for the next 24 hours, and surface the **squaring action** (buy/sell volume) for each interval ahead of gate closure.
  * **Imbalance watch:** Temporally join *Commercial Nominations* (what was promised) against *Real-Time Metering* (what assets actually produce), overlay the TSO system-balance direction, and project the **cash-out exposure** if the position is left unsquared.
  * **Backtest & replay before live:** Before a squaring or auto-bidding rule is trusted, **replay** historical continuous-market intervals using **Delta time-travel** and Spark-scale simulation, and track each strategy variant's realized P&L, hit-rate, and cash-out avoided in **MLflow**. The same gold tables that drive the live page feed the backtest, so research and production share one source of truth — the research-to-production loop that mirrors the long-term VaR rigor.
* **Demo headline:** an alerting view that flags assets in severe "forecast deviation," shows the gate-closure countdown per zone, quantifies the euro cost of staying short/long into delivery, and lets the desk **replay yesterday** to prove a squaring rule would have paid off before arming it live.

---

## Capability 2: 24/7 Operations & Live Dispatch (Control Tower)

The centerpiece of the module: a **control-tower dashboard** that runs the physical portfolio around the clock from a single operations view. It fuses asset telemetry, market gates, grid signals, and event feeds so an on-shift operator can see the whole book at a glance, act on the highest-value dispatch decision, and hand over cleanly to the next shift.

* **The Databricks Fit:** Structured Streaming (Real-Time Mode) + Mosaic AI Model Serving (dispatch policy) + Lakehouse Monitoring + an **agentic trading copilot** (Agent Bricks / multi-agent supervisor over Genie + Vector Search) + Databricks Apps (the live dashboard).
* **What the desk does:** co-optimize flexible assets (battery, CCGT, hydro) across Intraday, Day-Ahead, and TSO balancing markets (aFRR/mFRR) in real time, while continuously monitoring net imbalance, grid frequency, and REMIT outage events. Mosaic AI serves the dispatch policy that recommends the optimal action per asset — **Charge / Hold / Discharge**, **Ramp up/down**, **Bid into aFRR** — given live SoC, degradation limits, order-book depth, and frequency signals.

### Control-tower dashboard zones (conceptual)

| Zone | What it shows | Operator question |
| --- | --- | --- |
| **Portfolio balance ribbon** | Net long/short vs nominations across zones; TSO system-balance direction; projected cash-out (€) | *Am I balanced into the next intervals?* |
| **Asset dispatch panel** | Per-asset live state — battery SoC & cycle budget, CCGT clean-spark-spread & ramp state, hydro head — with the **recommended action** and expected margin | *What should each asset do right now?* |
| **Grid & frequency panel** | Live grid frequency, aFRR/mFRR activation signals, reserve obligations | *Is the grid short or long, and am I being called?* |
| **Market gate panel** | Countdown to the next DA/ID auction and XBID continuous gate per zone; live order-book depth/liquidity | *How long until I must act, and is there liquidity?* |
| **Event & REMIT feed** | Streamed outage/REMIT messages, weather shocks, ranked by bidding-zone and merit-order impact | *What just changed, and how big is it?* |
| **Trading copilot** | Agentic assistant that triages the event feed, retrieves similar past events (Vector Search), queries live tables (Genie), and **drafts a recommended action** with rationale for the operator to accept or reject | *What's the play, and why?* |
| **Alerts & shift handover** | Open actions, threshold breaches, P&L since shift start, handover notes | *What must the next shift not drop?* |

* **The copilot in detail:** an **Agent Bricks / multi-agent supervisor** sits over the lakehouse — one agent watches and classifies streamed REMIT/weather events, one retrieves precedent and merit-order impact via **Vector Search**, one queries live position and market tables via **Genie** — and the supervisor composes a single grounded recommendation (e.g. *"900 MW FR nuclear trip → DE intraday likely +€18/MWh for 4h: discharge battery 80 MW, bid 60 MW DSR into balancing"*). The operator keeps the decision; the agent removes the analytical lag.
* **Demo headline:** an operator watches a 900 MW thermal trip hit the **event feed**, the **balance ribbon** flip the portfolio short, the **trading copilot** draft "discharge battery + bid DSR into balancing" with its reasoning, the operator accept it, and the **P&L** hold — all without leaving the control tower.

---

## Capability 3: DSR & Market Access

Demand-Side Response (DSR) and Market Access turn thousands of small, distributed flexible assets into a single tradable **virtual power plant (VPP)**. The desk aggregates contracted flexibility, prequalifies it for wholesale and TSO balancing markets, dispatches it against price and grid signals, and settles the realized value back to the third-party asset owners — a route-to-market that monetizes flexibility the desk does not physically own.

* **The Databricks Fit:** Lakeflow / Structured Streaming for high-cardinality submeter ingest + Mosaic AI (baseline & availability forecasting) + Spark optimization (bid-stack aggregation) + Unity Catalog & Delta Sharing (multi-tenant governance and owner settlement) + Genie / AI-BI (availability views).
* **What the desk does:**
  * **Ingest & baseline:** Stream high-cardinality submeter telemetry from the VPP asset registry; ML models compute each asset's **counterfactual baseline** and **available flexibility** (MW up/down) per interval.
  * **Aggregate & qualify:** Roll thousands of assets into prequalified bid stacks that meet TSO product rules (minimum size, response time, sustain duration) for aFRR/mFRR and capacity, plus wholesale Intraday blocks.
  * **Dispatch & verify:** When prices spike or the grid is short, dispatch the optimal subset of assets; verify delivered response against baseline using metered data.
  * **Settle & share:** Allocate realized market value to each asset owner; expose governed, per-owner settlement and availability data via **Unity Catalog / Delta Sharing**.
* **Demo headline:** a midday negative-price event triggers the VPP to **absorb** flexible demand (charging EV depots, pre-cooling industrial loads), then an evening scarcity event **dispatches** the same portfolio into balancing — with per-owner settlement produced automatically and shared securely.

---

### Summary Table: Short-Term Tech Stack Mapping

| # | Capability | Core Prompt Challenge | Databricks Components to Highlight |
| --- | --- | --- | --- |
| **1** | **Trading near delivery** | Re-forecast and square the physical delta before gate closure; avoid cash-out; prove rules before going live | Structured Streaming (Real-Time Mode) + Lakeflow DLT + Multi-Stream Temporal Joins + Delta time-travel & MLflow (backtesting) |
| **2** | **24/7 Operations & Live Dispatch** | Run and co-optimize the whole physical book live, with event-driven response and an agentic copilot | Mosaic AI Model Serving + Lakehouse Monitoring + Agent Bricks (multi-agent) + Vector Search & Genie + Databricks Apps |
| **3** | **DSR & Market Access** | Aggregate, qualify, dispatch, and settle distributed third-party flexibility | Lakeflow high-cardinality ingest + Mosaic AI + Spark optimization + Unity Catalog & Delta Sharing |

---

*Cross-desk handoff: the curve desk's forward-curve and portfolio-risk outputs define the hedge position this desk inherits at delivery. Implementation conventions for notebooks, tables, and app pages will live in [`instructions.md`](./instructions.md).*
