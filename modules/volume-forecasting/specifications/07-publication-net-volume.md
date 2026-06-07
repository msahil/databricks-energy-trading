# 07 — Publication & Net-Volume Reconciliation

> Parent brief: [`main.md`](./main.md) (Capability 07). Platform and app conventions: [`instructions.md`](./instructions.md).

## Summary

Combine the demand legs (01 consumption, 02 long-term, 03 industrial) and the supply legs (05 wind, 06 solar) into a **single, reconciled net volume per zone per interval** — and **publish** it as the **official, versioned source of truth** every trading desk reads. This is where forecasting becomes a governed product: net volume is **immutable once published**, carries an `as_of_ts` and `publication_status`, and supersedes prior vintages without overwriting them (Delta time-travel keeps the audit trail).

No desk should reconcile raw capability outputs themselves — they read the **published** net volume. This capability owns the reconciliation logic (including the BTM-PV de-duplication between 04 and 06), the publication lifecycle, and the consumer-handoff contract. Data is **synthetic**; the publication and versioning pattern is production-shaped.

## Databricks fit

| Capability | Role |
|---|---|
| **Delta (MERGE + time-travel)** | Versioned publish; immutable vintages; full audit of supersessions |
| **Lakeflow Declarative Pipelines** | Reconcile demand + supply → net → publish with expectations |
| **Unity Catalog (Delta Sharing)** | Governed, access-controlled handoff to trading desks |
| **Lakehouse Monitoring** | Publication SLA: completeness and timeliness of the official cut |

## Notebook and tables

[`../notebooks/07_publication_net_volume.ipynb`](../notebooks/07_publication_net_volume.ipynb) materialises:

| Layer | Tables |
|---|---|
| Gold — official | `volume_forecast_gold_net_volume` |
| Gold — lifecycle | `volume_forecast_gold_publication_log` |
| Gold — contract | `volume_forecast_gold_consumer_handoff` |

Consumes: 01 `silver_consumption_st`, 02 `gold_consumption_lt_shape`, 03 `silver_industrial_load`, 05 `silver_wind_forecast`, 06 `silver_solar_forecast`, 04 `silver_btm_pv`. Run **after** 01–06.

**Catalog.schema:** `energy_utilities.energy_trading2`. **Grain (illustrative):** `delivery_date` × `zone_code` × `interval_start` × `publication_version`. The latest `PUBLISHED` version per interval is the official cut.

---

## Publication workflow

| # | Trader / risk intent | Data / UI outcome |
|---|---|---|
| 1 | What's the **official net volume** now? | `volume_forecast_gold_net_volume` latest `PUBLISHED` version |
| 2 | How does **supply vs demand** net out? | `total_demand_mw` − `total_supply_mw` = `net_volume_mw` |
| 3 | Which **version** am I on, and **as of when**? | `publication_version`, `as_of_ts`, `publication_status` |
| 4 | What **changed** since the last cut? | `net_volume_mw − prev_published_mw` (`revision_mw`) |
| 5 | Is the cut **complete** enough to publish? | `volume_forecast_gold_publication_log.completeness_pct`, gate |
| 6 | Who is **consuming** this and how? | `volume_forecast_gold_consumer_handoff` contract rows |

**Publication gate (illustrative):** a cut moves `DRAFT → PUBLISHED` only when all five legs are present and `completeness_pct ≥ 99`; otherwise it stays `DRAFT` and the prior `PUBLISHED` version remains the source of truth.

---

## Datasets

### Gold — `volume_forecast_gold_net_volume`

**The official, versioned net volume** — grain `delivery_date` × `zone_code` × `interval_start` × `publication_version`.

| Column | Type | Description |
|---|---|---|
| `delivery_date` | DATE | Day |
| `interval_start` | TIMESTAMP | Interval |
| `zone_code` | STRING | FK → zones |
| `publication_version` | INT | Monotonic version per interval |
| `consumption_st_mw` | DOUBLE | Short-term demand leg (01) |
| `industrial_mw` | DOUBLE | Industrial baseline leg (03) |
| `total_demand_mw` | DOUBLE | Sum of demand legs |
| `wind_mw` | DOUBLE | Wind supply leg (05) |
| `solar_mw` | DOUBLE | Utility-scale solar leg (06) |
| `btm_pv_mw` | DOUBLE | BTM PV (already netted in demand via 04) |
| `total_supply_mw` | DOUBLE | Sum of supply legs (no BTM double-count) |
| `net_volume_mw` | DOUBLE | `total_demand_mw − total_supply_mw` (signed) |
| `prev_published_mw` | DOUBLE | Prior `PUBLISHED` net volume |
| `revision_mw` | DOUBLE | `net_volume_mw − prev_published_mw` |
| `publication_status` | STRING | `DRAFT`, `PUBLISHED`, `SUPERSEDED` |
| `as_of_ts` | TIMESTAMP | When this version was cut |

### Gold — `volume_forecast_gold_publication_log`

Publication lifecycle / SLA — grain `delivery_date` × `zone_code` × `publication_version`.

| Column | Type | Description |
|---|---|---|
| `delivery_date` | DATE | Day |
| `zone_code` | STRING | FK → zones |
| `publication_version` | INT | Version published |
| `published_ts` | TIMESTAMP | Publish time |
| `legs_present` | INT | Count of input legs available (target 5) |
| `completeness_pct` | DOUBLE | Interval completeness of the cut |
| `gate_status` | STRING | `DRAFT`, `PUBLISHED`, `BLOCKED` |
| `superseded_version` | INT | Version this one replaced (null for first) |
| `note` | STRING | Reason / context for the cut |

### Gold — `volume_forecast_gold_consumer_handoff`

Consumer contract — one row per downstream consumer of the official volume.

| Column | Type | Description |
|---|---|---|
| `consumer` | STRING | `SHORT_TERM_SQUARING`, `LONG_TERM_CURVE`, `DSR_BIDSTACK`, `RISK`, `REPORTING` |
| `zone_code` | STRING | FK → zones |
| `handoff_field` | STRING | Field consumed (e.g. `net_volume_mw`) |
| `cadence` | STRING | `INTRADAY`, `DAILY`, `SEASONAL` |
| `latest_version` | INT | Version the consumer last read |
| `sla_minutes` | INT | Freshness SLA |

---

## App UI (Dash) — published net volume

| Item | Value |
|---|---|
| **Route** | `/volume-forecasting/publication` |
| **Sidebar label** | Publication & Net Volume |
| **Page module (convention)** | `app/pages/volume_forecast_publication.py` |
| **Data access** | `app/uc_pages.py` + `app/uc_sql.py`; header `sql-warehouse-dropdown` |

### Page layout

| Block | Content |
|---|---|
| **Hero** | Eyebrow, title, "single source of truth" summary, **Presenter guide** button |
| **Toolbar** | Date, zone, version selector (compare versions) |
| **Status banner** | Current version, as-of, publication status, completeness |
| **Outcome cards** | Net volume, total demand, total supply, revision since last cut |
| **Net volume chart** | Net volume by interval (demand − supply waterfall) |
| **Supply/demand stack** | Wind/solar/BTM vs consumption/industrial |
| **Version diff strip** | `revision_mw` vs prior published version |
| **Consumer handoff table** | Who reads this, cadence, SLA, version |
| **Presenter guide** | Problem → governance → story → who uses |

### Presenter guide (in-app modal)

| Section | Message |
|---|---|
| What problem this solves | One reconciled, governed net volume every desk trades against — no spreadsheet drift |
| Why governance matters | Published versions are immutable; supersessions are auditable (Delta time-travel) |
| Story to tell | Demand + supply → net → publish gate → version & as-of → who consumes it |
| Who uses this view | All trading desks, risk, reporting, management |

### Widget-to-dataset binding

| UI block | Primary datasets | Key fields |
|---|---|---|
| Status banner | `volume_forecast_gold_publication_log` | `publication_version`, `published_ts`, `completeness_pct`, `gate_status` |
| Outcome cards | `volume_forecast_gold_net_volume` | `net_volume_mw`, `total_demand_mw`, `total_supply_mw`, `revision_mw` |
| Net volume chart | `volume_forecast_gold_net_volume` | `interval_start`, `net_volume_mw` |
| Supply/demand stack | `volume_forecast_gold_net_volume` | `wind_mw`, `solar_mw`, `consumption_st_mw`, `industrial_mw` |
| Consumer handoff table | `volume_forecast_gold_consumer_handoff` | `consumer`, `cadence`, `sla_minutes`, `latest_version` |

### Empty and error states

| Condition | Message / behaviour |
|---|---|
| No warehouse selected | Prompt to select a running warehouse |
| Warehouse selected, no data | Prompt to run `energy_trading_demo_data` (needs 01–06 first) |
| Query failure | Show error text; do not fabricate charts |

---

## Relationships

| Direction | Dependency |
|---|---|
| **Upstream** | **01, 02, 03** demand legs; **05, 06** supply legs; **04** BTM PV for de-duplication |
| **Downstream** | **Short-term squaring** (single source of truth for net position); long-term curve; DSR bid stack; **08** scores the published cut |
| **Shared** | Consumes zones / intervals from 04 |

This capability is the module's **contract boundary**: schema changes to `volume_forecast_gold_net_volume` ripple into every consuming desk and into 08. Coordinate before changing the published grain or `publication_status` semantics.

## Out of scope

- Real cross-desk delivery / messaging integration (Delta Sharing pattern documented)
- TSO submission / nomination formats (illustrative handoff only)
- Settlement reconciliation (08 handles accuracy; settlement is a downstream desk concern)
- In-app mock or generated series (see [`instructions.md`](./instructions.md))
