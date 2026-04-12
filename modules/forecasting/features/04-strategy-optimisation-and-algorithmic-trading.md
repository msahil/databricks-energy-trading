# Strategy, optimisation and algorithmic trading — specification (Europe)

**Parent brief:** [input.md](./input.md)

## Demo data (notebook and tables)

Synthetic demo for this capability is created by [**`04_strategy_optimisation_and_algo_trading.ipynb`**](../notebooks/04_strategy_optimisation_and_algo_trading.ipynb) (run as **4 of 4** in the sequence in [`README.md`](../README.md)). It materialises **Delta** tables in Unity Catalog under the default location **`energy_utilities`.`energy_trading2`** (override with `DEMO_UC_*` env vars in [`demo_data/notebook_helpers.py`](../demo_data/notebook_helpers.py)). Use these tables when wiring the [Databricks App](../../../app/) to catalogued data instead of local-only synthetic helpers.

**UI (inherited):** When implementing widgets for this capability, follow [UI implementation — inherited instructions](./input.md#ui-inherited-instructions) in `input.md`—use a **consistent theme** with the rest of the app, bind widgets **explicitly** to this notebook and the `demo_*` tables below, and write **titles, tooltips, and footnotes** that describe the capability and the meaning of the demo columns (not generic chart labels).

| Delta table | Description (demo) |
|-------------|-------------------|
| `demo_strategy_definitions` | Parameterised strategy definitions |
| `demo_backtest_summary` | Backtest summary metrics per strategy |
| `demo_alert_rules` | Threshold / alert rule definitions |
| `demo_alert_events` | Synthetic alert events |
| `demo_dashboard_kpis` | KPI-style monthly aggregates |
| `demo_tso_market_events` | Market / TSO event log (operational context) |
| `demo_viz_series_long` | Long-format series for charts |
| `demo_forecast_vs_actual` | Forecast vs actual error series |
| `demo_forecast_scope_catalog` | Forecast scope / use-case catalogue |
| `demo_scenario_definitions` | Stress / scenario labels |
| `demo_user_personas` | Demo user / persona rows |

## 1. Purpose

Support repeatable research on trading ideas and hedging rules, optimisation of nominations and hedges under stated constraints, and—where the organisation is licensed and technically connected—automated order submission with controls that reflect European wholesale practice: REMIT-related surveillance inputs, pre-trade risk, and operational resilience (kill switches, reconciliation).

Assisted workflows (parameterised rules, templates, documentation) are preferred to vague “AI agent” claims: every production strategy has an owner, version, and approval trail.

## 2. Scope

| In scope | Out of scope |
|----------|----------------|
| Backtesting with documented costs and constraints | Promised returns or alpha |
| Optimisation for hedges, nominations, storage (if assets in scope) | Real-time DCS control of generators |
| Semi-automated or automated execution via approved OMS or broker APIs | Unsupervised self-modifying strategies without governance |

**Markets:** continuous intraday power (SIDC), balancing and ancillary products where traded, short-term gas products as licensed—not all products are available to all participants.

## 3. Stakeholders

- Traders and analysts (hypothesis, parameters).
- Quant (implementation, backtest integrity).
- Risk (limits, stress).
- Compliance (market-abuse design inputs, algorithm inventory where MiFID II applies to the entity).
- IT (deployment, monitoring, incidents).

## 4. Functional requirements

### 4.1 Assisted strategy specification

- **Parameterised definitions:** universe (EIC codes, products), entry/exit rules, horizon, position sizing—via forms or notebook templates, not only unstructured text.
- **Documentation:** plain-language description, data dependencies, code version or no-code graph id stored with each strategy version.
- **Guardrails:** warnings or blocks on lookahead in features; enforcement of point-in-time joins from governed tables.
- **Outputs:** backtest report (§4.2), parameter sensitivity, export for risk committee or internal review.

### 4.2 Backtesting

- **Transaction costs:** exchange fees where known; bid–ask assumptions appropriate to SIDC liquidity (product- and hour-specific where possible).
- **Slippage:** fixed, volume-dependent, or volatility-linked models—documented and reviewable.
- **Liquidity:** maximum volume per interval; partial fill or no-fill rules for continuous markets.
- **Latency:** assumed delay from signal to order receipt at venue or broker—critical for intraday.
- **Conduct:** backtests must not assume wash trades or fictitious liquidity; design notes reference surveillance relevance (REMIT Article 2 concepts—operational implementation via compliance).
- **Metrics:** net PnL, drawdown, Sharpe (with caveats for non-Gaussian returns), turnover, capacity utilisation; stability across sub-periods.

### 4.3 Portfolio and asset optimisation

- **Objectives:** margin maximisation, risk minimisation, or constrained utility (e.g. CVaR limit)—user-selected within policy.
- **Constraints:** contractual (PPA, CfD, balancing agreements); physical (ramp rates, min load) where modelled; grid (nomination limits, ATC where data exists); regulatory must-run or support-scheme parameters only if data is available to the desk.
- **Horizons:** intraday (next hours), day-ahead plan, rolling hedge for weeks or months.
- **Storage:** only if assets and metering data are in scope; SOC dynamics, efficiency, degradation as optional detail.

### 4.4 Algorithmic and automated trading

- **Modes:** shadow (paper), human confirm, fully automated—promotion gated by policy.
- **Pre-trade:** position vs limit, notional caps, concentration, credit for OTC; halt detection if a market status feed exists.
- **Risk limits:** per strategy, per book, aggregate; freshness of limit cache bounded by SLA.
- **Kill switch:** global and per-strategy; manual always available; automatic on sustained error rate, feed loss, or hard limit breach.
- **Model-driven logic:** same controls as rules; pinned model version; deterministic fallback (e.g. flat position) on invalid input.

### 4.5 Monitoring and incident

- **Dashboards:** PnL by strategy, orders, fills, rejects, latency histograms.
- **Alerting:** on-call path for kill events, reconciliation breaks, limit breaches.
- **Reconciliation:** orders vs broker or exchange confirmations; break workflow.

## 5. Non-functional requirements

- **Determinism:** backtest replay with fixed seed and data snapshot.
- **Latency:** end-to-end targets per venue documented (not a single number for all markets).
- **Security:** API keys in vault; separate credentials per environment.
- **Degraded mode:** halt new orders if risk or reference data is stale beyond threshold.

## 6. Interfaces

- **Data:** market data and forecasts from specs 01 and 03.
- **Execution:** OMS or broker FIX/REST adapters—no direct exchange API unless explicitly in roadmap.
- **Risk:** limits service; positions feed.

## 7. Success criteria

- Template strategies completable by non-developers in UAT without ad hoc engineering (measured in user acceptance tests).
- Backtest reports reconcile gross to net via documented cost lines (review sample in model risk or quant sign-off).
- Production algo: no unmitigated limit breaches (definition by risk); documented MTTR for incidents involving the kill switch.

## 8. Open points

- MiFID II algorithmic-trading obligations apply to investment firms and certain other entities—inventory and documentation owned by compliance; energy merchant status varies by entity.
- European balancing platforms (e.g. PICASSO/MARI evolution) change over time—integration scope per TSO roadmap.
