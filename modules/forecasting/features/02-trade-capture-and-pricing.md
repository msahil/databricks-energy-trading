# Trade capture and pricing — specification (Europe)

**Parent brief:** [input.md](./input.md)

## Demo data (notebook and tables)

Synthetic demo for this capability is created by [**`02_trade_capture_and_pricing.ipynb`**](../notebooks/02_trade_capture_and_pricing.ipynb) (run as **2 of 4** in the sequence in [`README.md`](../README.md)). It materialises **Delta** tables in Unity Catalog under the default location **`energy_utilities`.`energy_trading2`** (override with `DEMO_UC_*` env vars in [`demo_data/notebook_helpers.py`](../demo_data/notebook_helpers.py)). Use these tables when wiring the [Databricks App](../../../app/) to catalogued data instead of local-only synthetic helpers.

**UI (inherited):** When implementing widgets for this capability, follow [UI implementation — inherited instructions](./input.md#ui-inherited-instructions) in `input.md`—use a **consistent theme** with the rest of the app, bind widgets **explicitly** to this notebook and the `demo_*` tables below, and write **titles, tooltips, and footnotes** that describe the capability and the meaning of the demo columns (not generic chart labels).

| Delta table | Description (demo) |
|-------------|-------------------|
| `demo_trades_otc_remit_style` | Synthetic OTC deals with REMIT-shaped fields |
| `demo_consumer_contracts` | Consumer / contract registry rows |
| `demo_downstream_exports` | Downstream export / handoff metadata |

## 1. Purpose

Record deals and positions in a form that matches European wholesale practice: EFET/ISDA-style economic terms, REMIT-reportable fields, EMIR derivatives identifiers where applicable, and marking that risk and finance can replay. The platform is the contractual source of truth for captured trades; CCP statements and settlement files reconcile against it.

## 2. Scope

| In scope | Out of scope (unless added later) |
|----------|-----------------------------------|
| OTC and voice capture, imports, APIs from internal execution tools | Direct market access to exchange matching engines |
| Data required for REMIT and EMIR reporting workflows | Legal classification of reporting obligation |
| Marking and valuation using curves and vol from the market-data layer | Full exotic pricing library (may integrate external library or vendor) |

**Instruments** (as used by the business): forwards, swaps, futures, options, PPAs, capacity rights, balancing/ancillary/system products where traded, standard gas contracts—each defined in a product catalog with risk sign-off.

## 3. Stakeholders

- Front office (traders, originators).
- Middle office (confirmations, marks).
- Risk (limits, Greeks, stress).
- Compliance (REMIT, EMIR, market-abuse inputs).
- Operations (settlements interface).

## 4. Functional requirements

### 4.1 Trade capture

- **Channels:** manual entry, CSV/API bulk, interfaces from approved execution or workflow tools.
- **Validation:** mandatory fields before commit; configurable warnings for unusual tenor or price.
- **Minimum attributes:**
  - **Underlying:** bidding zone (EIC), gas virtual trading point/hub, or emissions product as defined in catalog.
  - **Delivery:** start and end (datetime with timezone Europe/Berlin or UTC per policy); profile (baseload, peak, shaped, hourly, quarter-hourly where used).
  - **Volume and unit:** MWh, MW, exchange lot size per contract.
  - **Price:** fixed, floating index (formula with publication lag), currency; FX hedge link if cross-currency.
  - **Counterparty:** legal entity; LEI where EMIR or policy requires.
  - **Documentation:** EFET/ISDA master reference; CSA flag for collateral.
  - **Clearing:** bilateral vs cleared (CCP name, account); affects margin and EMIR reporting.

### 4.2 Product types

- **Linear:** forwards, CFDs, swaps—map to risk factors (underlying, delivery period).
- **Options:** strike, expiry, style (European typical for exchange-traded power options); link to vol surface id for valuation.
- **PPAs:** fixed volume vs pay-as-produced; floor/ceiling/collar; GO linkage if certificates are bundled.
- **Structured:** multi-leg; embedded optionality (swing, take-or-pay)—store leg definitions and external valuation model id if the internal engine does not price the full payoff.

### 4.3 Pricing and valuation

- **Curves:** mark using official or desk curves from [01-market-data-and-visualisation.md](./01-market-data-and-visualisation.md); interpolation (e.g. linear on log prices) documented per product class.
- **Options:** vol surface per underlying and tenor grid; Greeks where the library supports; scenario shocks (parallel shift, skew stress) for risk.
- **Marks:** EOD batch; optional intraday for selected books; override with audit trail (optional four-eyes per policy).
- **Multi-commodity:** power + gas + EUA legs with explicit settlement calendar and rounding.

### 4.4 Regulatory and operational data

- **REMIT:** capture reportable transaction fields per the organisation’s mapping to ACER schemas; export to Registered Reporting Mechanism (RRM) or internal hub in the XML/format required by implementing acts (as updated over time).
- **EMIR (Refit where applicable):** UTI generation or ingestion, counterparty identifiers, clearing threshold flags, C/P indicator—handoff to trade-repository workflow per compliance.
- **Audit:** immutable event log (create, amend, cancel); user, timestamp, reason code for amendments.

### 4.5 Lifecycle

- **Novation and amendment:** versioned economic terms; effective dates.
- **Termination:** break fee or close-out amount; final payment date.
- **Confirmation:** status workflow (pending, matched, disputed) with export to confirmation platform if used.

## 5. Non-functional requirements

- **Consistency:** positions derive from trades and market data; no manual position without a trade or adjustment record.
- **Performance:** revaluation batch completes within agreed window after marks are available.
- **Access:** role-based; information barriers between desks if policy requires.

## 6. Interfaces

- **Inbound:** blotter feeds, manual UI, APIs.
- **Outbound:** risk engine, PnL, REMIT/EMIR pipelines, warehouse for analytics.

## 7. Success criteria

- Mandatory attributes enforced at entry (exceptions logged and approved).
- Sample REMIT/EMIR exports validate against published schema versions used in UAT.
- Mark-to-market reconciles to the risk system within defined tolerance for vanilla products.

## 8. Open points

- RRM and trade-repository connectivity are often third-party—interface spec owned by integration.
- EMIR UK vs EU regimes for UK counterparties—mapping per legal advice.
