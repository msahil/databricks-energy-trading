# Market data and visualisation — specification (Europe)

**Parent brief:** [input.md](./input.md)

## Demo data (notebook and tables)

Synthetic demo for this capability is created by [**`01_market_data_and_visualisation.ipynb`**](../notebooks/01_market_data_and_visualisation.ipynb) (run as **1 of 4** in the sequence in [`README.md`](../README.md)). It materialises **Delta** tables in Unity Catalog under the default location **`energy_utilities`.`energy_trading2`** (override with `DEMO_UC_*` env vars in [`demo_data/notebook_helpers.py`](../demo_data/notebook_helpers.py)). Use these tables when wiring the [Databricks App](../../../app/) to catalogued data instead of local-only synthetic helpers.

**UI (inherited):** When implementing widgets for this capability, follow [UI implementation — inherited instructions](./input.md#ui-inherited-instructions) in `input.md`—use a **consistent theme** with the rest of the app, bind widgets **explicitly** to this notebook and the `demo_*` tables below, and write **titles, tooltips, and footnotes** that describe the capability and the meaning of the demo columns (not generic chart labels).

| Delta table | Description (demo) |
|-------------|-------------------|
| `demo_reference_bidding_zones` | Reference bidding zones (EIC-style) |
| `demo_prices_spot_hourly` | Hourly spot-style prices (zones, venue, €/MWh) |
| `demo_bronze_prices_spot` | Bronze-layer raw feed (lineage-style) |
| `demo_entsoe_transparency_style` | ENTSO-E Transparency–style actuals |
| `demo_german_imbalance_prices_style` | German imbalance price–style series |
| `demo_nwp_ecmwf_surface_style` | NWP-style surface parameters |
| `demo_gas_hub_ttf_style` | TTF-style gas hub series |
| `demo_eua_ets_daily_style` | EU ETS allowance–style daily CO₂ |
| `demo_grid_signals` | TSO / grid metric time series |
| `demo_fundamentals_de_lu` | Zone fundamentals (temp, wind, solar, load, residual) |
| `demo_cross_border_flows` | Cross-border flow-style MW series |

## 1. Purpose

Provide **ingestion**, **storage**, **cataloguing**, and **consumption** of data that European power and gas desks actually use: **exchange and broker prices**, **derivatives** settlements, **TSO and ENTSO-E system data**, **weather** and **commodity** inputs, and **internal marks**. Support **visualisation** (curves, spreads, heatmaps, time series) for **trading**, **risk**, and **research**, with **audit-grade** lineage and **as-of** reproducibility.

This document describes **what** the platform must support; **which** commercial feeds and licences apply is determined by procurement and compliance.

## 2. Scope

| In scope | Out of scope (unless added later) |
|----------|----------------------------------|
| Normalised **time series** and **reference data** for subscribed sources | Substitute for a **data vendor contract** or **exchange membership** |
| **Public** TSO/ENTSO-E data subject to terms of use | **Confidential** TSO data not licensed to the organisation |
| **Curve** and **surface** views built from licensed data | **Order routing** or **execution** (OMS) |
| **Unity Catalog** (or equivalent) governance on the lakehouse | On-prem **historian** replacement for plant SCADA |

**Geography:** Configurable **bidding zones** and **gas hubs** used by the business—typically **Central Western Europe** and **Nordics** for power; **TTF**, **THE**, **NBP**, and others per subscription.

## 3. Stakeholders

- Trading and origination (short-term and forward curves).
- Risk and product control (**marks**, **sensitivities**, **PnL** explain).
- Quantitative analysis and data science (**features**, **backtests**).
- Data engineering (pipelines, **SLAs**, **catalog** ownership).

## 4. Functional requirements

### 4.1 Ingestion — prices and derivatives

- **Power spot and short-term:** **Day-ahead** results from **single day-ahead coupling (SDAC)** and related processes; **intraday** continuous markets (**SIDC**); preserve **auction** vs **continuous** semantics, **delivery period** (e.g. PT60M, PT15M), **currency** (typically **EUR**), and **EIC** or venue **product code** in metadata.
- **Derivatives:** **Futures and options** on licensed venues (e.g. **EEX** power and gas, emissions); store **settlement**, **last trade**, **open interest** per source definition; support **rolling** and **seasonal** products as defined by the exchange.
- **Gas:** **Hub** and **VP** prices, **forward** curves from vendors or exchanges; store **energy unit** (MWh, therms) and **gas day** / **delivery** rules per **hub** specification.
- **Broker runs:** **OTC** assessments or **contributed** curves where contracted; treat **timestamp** and **contributor** as mandatory fields.

### 4.2 Ingestion — system and transparency

- **ENTSO-E Transparency Platform** (and successors): **actual generation** by type where published, **load**, **cross-border** flows and **scheduled** exchanges, **unavailability** where available—subject to **update frequency** and **lag** documented per series.
- **National TSOs** (e.g. in Germany: **50Hertz**, **Amprion**, **TenneT DE**, **TransnetBW**): **imbalance** prices and volumes, **balancing** information published for the market area, **forecasts** where published—**schema** may differ; normalise in **silver** layers with **source system** preserved in **bronze**.
- **Outages and unavailability:** **UMM**-style messages or national equivalents where used for trading; map to **EIC** of **production units** where possible.

### 4.3 Ingestion — weather and commodities

- **Weather:** **NWP** grids or site forecasts used for **load** and **renewables** (e.g. **ECMWF**, **DWD ICON**, commercial vendors); store **run time**, **horizon**, and **resolution**; support **wind** (e.g. hub-height), **irradiance** (GHI/DNI as used by models), **temperature**.
- **Commodities:** **TTF** or other **gas** spot/forward as subscribed; **EU ETS** allowance (**EUA**) prices for **clean spark / dark** style analytics where the desk requires them.

### 4.4 Data quality and governance

- **Versioning:** Immutable **bronze**; **restated** series (e.g. TSO corrections) either **append** with **effective** timestamps or **version** rows—policy per dataset.
- **Lineage:** Pipeline → **table** → **column** traceability; **transformation** code versioned (e.g. git hash).
- **Quality flags:** **Stale** feed, **missing** period, **spike** detection; optional **quarantine** workflow before **silver** promotion.
- **Reference data:** **EIC** codes, **bidding zone** borders, **holiday** calendars (including **exchange** calendars), **product** definitions aligned to **EEX** / **EPEX** / **Nord Pool** as used.

### 4.5 Marks and curves

- **Official / desk marks:** **End-of-day** (and intraday if policy) **marks** with **as-of** timestamp locked for **PnL** runs.
- **Separation:** **Vendor and exchange** truth must not be overwritten by **model** or **manual** curves; separate **namespace** or **table** with **provenance** (user id, model id, run id).
- **Derived:** **Spreads** (e.g. **DE-LU** vs **FR**, **DA** vs **ID**), **implied vol** from listed options where pricing library exists.

### 4.6 Analytics and ML (on platform data)

- **Feature store:** Lagged prices, **weather**, **TSO** series with **point-in-time** joins for **backtesting** (no **future** columns).
- **Operational:** **Anomaly** detection on feeds; **short-horizon** **nowcasts** for dashboards—clearly labelled as **non-official** vs **regulated** forecasts if that distinction exists in the organisation.

### 4.7 Visualisation

- **Curves:** By **tenor** and **zone/hub**; toggle **source** (exchange vs broker vs internal).
- **Heatmaps:** e.g. **hour** × **day** or **tenor** × **zone** for price or **spread**.
- **Time series:** Overlay **price** with **load** or **renewable** forecast for **post-trade** analysis.
- **Drill-down:** Book → **trade** / **contract** (requires position/trade integration; see [02-trade-capture-and-pricing.md](./02-trade-capture-and-pricing.md)).
- **Order book:** Only if **licence** and **technical** feed exist; show **latency** and **snapshot** time.

## 5. Non-functional requirements

- **Latency:** Targets defined **per feed class** (e.g. **ticker** for screens vs **EOD batch**); document **vendor**-limited delays honestly.
- **Retention:** **Hot** vs **archive** per **legal** and **cost** policy; **partition** by **date** and **source**.
- **Security:** **Row** or **column**-level policies where **desks** must be isolated; **secrets** in vault; **audit** on **mark** changes.
- **Availability:** **Replay** or **backfill** after outage; **monitoring** on **freshness** vs **SLA**.

## 6. Interfaces

- **Inbound:** APIs, SFTP, **Kafka**, file drop—**bronze** first, then **normalised** layers.
- **Outbound:** **SQL warehouse**, **REST** for apps, **notebooks**; **exports** to **risk** systems in agreed formats.

## 7. Success criteria

- A **single catalog** lists **instruments** and **series** with **documented** **owner** and **freshness**.
- **Curve** and **fundamental** views are used **without** recurring **ad hoc** CSV **extracts** for standard workflows.
- For a given **as-of** date, **analysts** can **reproduce** a **feature** table used in a **model** (audit / model risk).

## 8. Open points

- **Exact** **symbol** and **product** maps are **vendor**-specific and maintained as **reference data**.
- **Quarter-hourly** vs **hourly** **imbalance** and **intraday** **products** depend on **market area**—**mapping** tables per **country**.
