# Energy trading platform — capability brief (Europe)

This folder defines **non-functional and functional requirements** for a data and analytics platform supporting **European wholesale power and gas** trading and risk. The intent is alignment with how these markets actually operate: **coupled day-ahead auctions**, **continuous intraday**, **derivatives clearing**, **TSO and ENTSO-E transparency**, **REMIT** and **EMIR** obligations, and **balancing / system** data that desks use for short-term decisions.

**Deliverable:** one detailed specification per capability (see table below).

### Detailed specification files

| Capability | Document |
|------------|----------|
| Market data and visualisation | [01-market-data-and-visualisation.md](./01-market-data-and-visualisation.md) |
| Trade capture and pricing | [02-trade-capture-and-pricing.md](./02-trade-capture-and-pricing.md) |
| Forecasting and predictive analytics | [03-forecasting-and-predictive-analytics.md](./03-forecasting-and-predictive-analytics.md) |
| Strategy, optimisation and algorithmic trading | [04-strategy-optimisation-and-algorithmic-trading.md](./04-strategy-optimisation-and-algorithmic-trading.md) |

### UI implementation — inherited instructions (Databricks App and capability UIs)

<a id="ui-inherited-instructions"></a>

**Scope.** The following applies to **every** detailed capability document in this folder (`01`–`04`), to the [Databricks App](../../../app/), and to any other UI built to showcase this accelerator. Child specs **inherit** these rules; they do not restate them—implementers must treat this section as the single UI contract alongside each spec’s functional requirements and **Demo data** block (notebook + Delta tables).

**Data binding — notebooks and demo tables.** UI work must be **grounded in the demo pipeline**, not only in prose:

- For each capability, use the **referenced demo notebook** and the **Delta table names** listed in that spec’s **Demo data (notebook and tables)** section. Prefer reading from Unity Catalog at the default location documented in [`README.md`](../README.md) (`energy_utilities`.`energy_trading2`, unless overridden by `DEMO_UC_*`).
- **Databricks App / SQL:** In the [Databricks App](../../../app/), **all** data shown in capability UIs must be read from the **corresponding `demo_*` Delta tables** (per capability spec) using the **currently selected SQL warehouse** in the app header—no hard-coded warehouses, no alternate ad hoc sources for “live” demo views. Queries and Statement Execution calls must target those UC tables so behaviour matches the notebooks and deployed demo data.
- **Map widgets to tables explicitly:** in design or code comments, state which chart, table, KPI, or filter is fed by which `demo_*` table (and key columns), so the UI reflects the **shape and meaning** of the synthetic data—not a generic placeholder.
- If a widget cannot yet bind to UC (e.g. local dev), it should still **mirror** the same logical fields and labels as the deployed demo tables so behaviour matches production.

**Data-driven widget design — apply every time.** Before specifying or building **any** widget that shows data (charts, tables, KPIs, filters, heatmaps), follow this order—**do not** design from the spec title alone or from assumed column names:

1. **Read the capability detailed spec** (the corresponding `0N-*.md` in this folder): **Demo data (notebook and tables)**, column semantics, units, zones, and what each table is meant to represent.
2. **Read the referenced demo notebook**: its **introduction / description**, how tables are built, joins, grains (e.g. hourly vs daily), and any notes on realistic ranges or filters.
3. **Sample the tables on a SQL warehouse** (the same **header SQL warehouse** the app will use): run exploratory SQL—e.g. `SELECT *` limited rows, `COUNT(*)`, `MIN`/`MAX` on time columns, `DISTINCT` on zone/product/series keys, simple aggregates—so you know **actual** column names, types, cardinalities, date coverage, and typical values. Adjust widget types, axes, legends, and default filters to match what is **in** the data, not what was guessed from prose.
4. **Then** design and implement widgets: choose chart types, KPI definitions, and filter controls grounded in steps 1–3; document the table → widget mapping as required above.

Repeat this workflow whenever **new** `demo_*` tables appear, schemas change, or you add or refactor capability UIs.

**Widgets and narration.** Each capability area should be represented by **purpose-built widgets** (time series, small multiples, KPI cards, data grids, filters, sparklines, etc.) that **explain what the desk would see** in that domain:

- **Titles and copy** must name the capability in **plain language** (e.g. ingestion lineage, REMIT-shaped trades, forecast skill, backtest vs costs) and tie directly to the **semantics of the demo columns** (units, zones, products, horizons)—not vague labels like “Chart 1”.
- Include **short descriptive text** per section or widget group: what the synthetic data **stands in for** (exchange/TSO/vendor-style feeds, regulatory fields, model metrics, strategy alerts), and that data is **demo-only** where applicable.
- **Tooltips, axis labels, legends, and footnotes** should be specific enough that a trader or analyst understands **what is being showcased** and how it relates to the bullet narrative in the parent brief and the detailed spec.

**Page and widget copy — business-first, spec-grounded.** Write for **customers and business users** (trading, risk, origination, analytics leadership), not only for engineers. **Page titles (`h1`)**, **intro blurbs** (the paragraph under the title), **section headings**, **chart titles**, **KPI card titles**, and **lead captions** should answer: *what business question does this view address*, and *what can a user infer for decisions or oversight*—using clear domain language (markets, zones, products, risk, freshness, governance). Derive wording from the **capability spec** (`0N-*.md`, including relevant §4.x themes) and from the **`demo_*` tables** actually wired to the page: the **business story comes first**; **technical identifiers** (table names, `product_code`, column names) belong in **secondary** lines—figure footnotes, table captions, or axis labels—so UC binding and auditability remain without sounding like an internal schema dump. When data is **synthetic or demo-only**, say so plainly where a user might assume a live vendor or exchange feed. **Register page `title` metadata** (browser tab) should also read like a product surface (e.g. “Prices & power derivatives”) rather than only an internal code name. Apply these rules to **every** capability page built under this contract.

**Page intro blurbs — tone and presentation.** The **paragraph(s) directly under the page `h1`** must read like a **short product brief** for a business audience, not like internal documentation. **Avoid** leading with platform or implementation jargon (e.g. “Unity Catalog”, “warehouse”, “Delta”, `demo_*` names, SQL constructs) in the first sentences—those belong in the **page footnote** or **widget captions** where traceability is required. **Do** lead with **outcomes**: what the user can see, compare, or decide (prices across regions, imbalance exposure, curve shape, data lineage for audit). Use **plain market language** (day-ahead, intraday, hubs, load, spreads, governance) instead of schema vocabulary unless the audience is technical.

**Descriptive depth (required).** Intros must be **substantive enough** that a new reader knows *why this page exists*, *who it is for*, and *what they will do with the charts*—not just a slogan. Aim for **one or two opening paragraphs** (about **four to ten sentences total**) that cover: the **business question** or workflow (e.g. morning briefing, spread monitoring, audit prep); **what is on the page** at a glance (which markets, products, or signals); and **how it connects** to neighbouring pages or decisions (risk, hedging, operations, compliance). Optional: a single sentence on **when** to use the page (e.g. before drilling into raw feeds, or when explaining locational risk to a stakeholder). **Do not** pad with filler; every sentence should add a concrete detail.

**Format for scanning.** After the opening prose, add **4–6 bullet lines**. Each line starts with a **bold label** (2–4 words) followed by a **short phrase or sentence** that explains *what the user gets* from that slice of the page—not a three-word stub. Prefer parallel structure across bullets. End with **one muted caveat paragraph** in *italics* (Markdown `*...*`) for demo vs live data and/or how to refresh—still in plain language. Implement intros with **`dcc.Markdown`** so **bold**, **bullets**, and **italics** render correctly—do not use raw `html.P` with fake `**` markers. The intro block (class **`page-intro-markdown`**) should use the **full width** of the main content column, consistent with charts and tables—styling lives in **`app/assets/custom.css`** (`.page-intro-markdown { width: 100%; max-width: none; }`), not a narrow `max-w-*` wrapper.

**Visual consistency.** All capability UIs must share a **single theme**: consistent **typography scale**, **spacing**, **colour roles** (e.g. primary series, baselines, alerts, neutral chrome), chart **heights and padding**, and **component patterns** (cards, rails, panels). New screens or routes must **extend** the existing Databricks App styling where present rather than inventing a one-off palette—so moving between capabilities feels like one product, not four disconnected demos.

**Layout — full width.** The main content area (beside the sidebar) must use the **available horizontal space** on the viewport: **do not** wrap capability pages in narrow `max-w-*` containers that leave a large empty band on wide screens. **KPI rows, chart panels, tables, heatmaps, and grid layouts** must span the **full width** of that main column, subject only to **consistent horizontal padding** (e.g. shared `px-*` on the page shell). Charts should stretch with their container (no fixed narrow column for figures). If introductory prose is used, it may use a comfortable line length, but **data widgets** must not sit in a half-width column with unused space beside them unless that unused space is intentional (e.g. a deliberate secondary panel documented in the spec).

**Loading — common rule for all app pages.** This applies to **every** [Databricks App](../../../app/) **page/route** that fills (or refreshes) the main content area through Dash **callbacks**—not only capability **01** and not only SQL. Any slow work counts: Unity Catalog / SQL warehouse queries, REST calls, or other async data fetch. **Requirement:** while that callback is in flight, users must see a **clear loading indicator**; when the callback finishes (success or error), the indicator **must disappear** and the rendered content (or error UI) must show. Implement this **consistently** using Dash **`dcc.Loading`** (or an equivalent pattern) wrapping the element whose **`children`** (or other props) the callback updates—prefer a **shared page layout helper** in the app so **new pages inherit the behaviour by default** and the spinner styling stays aligned with the theme (e.g. brand accent colour). If your Dash version supports **`delay_show`** on `dcc.Loading`, use a short delay (e.g. 100–250 ms) to reduce flicker on fast responses. **Exempt:** routes that are purely static with **no** data-loading callbacks (e.g. empty placeholders) until they gain such callbacks; then this rule applies.

**Review checklist.** Before shipping UI for a capability: (0) **Data-driven widget design** (above) was followed: spec + notebook read, and warehouse sampling used to validate tables before widget design; (1) notebook order and UC tables from [`README.md`](../README.md) have been run; (2) each major widget names its source table(s); (3) app queries use the **header SQL warehouse** and only the **capability’s `demo_*` Delta tables**; (4) theme matches the rest of the app; (5) on-screen text matches the **intent** of the spec and the **content** of the demo data; (6) **layout**: main content and widgets use **full width** of the app main column (no unnecessary narrow `max-w-*` on the page shell; charts and cards fill the padded content area); (7) **loading (app-wide)**: **all** pages that use callbacks to load or refresh data wrap the targeted output in **`dcc.Loading`** (or equivalent) per the common rule above—no page-specific exception unless the route has no data callbacks; (8) **copy**: page intros, headings, chart titles, and KPI labels are **business-first** per **Page and widget copy** above, with **technical table/column** detail in secondary captions or footnotes; (9) **intro blurbs** follow **Page intro blurbs — tone and presentation** (Markdown, **descriptive depth**, 4–6 substantive bullets, non-technical lead, italic caveat last).

### Geographic and commodity scope

- **Power:** bidding-zone level (e.g. **DE-LU**, neighbouring **FR**, **NL**, **BE**, **AT**, **PL**, **Nordics** as needed); products with **hourly** and **quarter-hourly** granularity where markets offer them (e.g. German intraday **15-minute** contracts).
- **Gas:** European **virtual trading points** and hubs (e.g. **TTF**, **THE**, others per licence); day-ahead and forward curves as subscribed.
- **Related:** **EU ETS** allowance prices where needed for thermal margin; **Guarantees of Origin** and other **certificate** trades if the business books them.
- **Context:** high **renewables** penetration, **cross-border coupling** (e.g. **SDAC** for day-ahead, **SIDC** for intraday), and **imbalance settlement** that varies by TSO ruleset—requirements must not assume a single global template.

---

## Market data and visualisation

**Ingestion and quality**

- **Exchanges and brokers:** day-ahead and intraday **power** (including **single day-ahead coupling** outcomes and **continuous intraday** / **SIDC** where licensed), **derivatives** (e.g. **EEX** and comparable venues), **gas** hub and forward prices; preserve **timestamp**, **currency**, **unit**, and **contract specification** exactly as defined by the source.
- **System operators:** **ENTSO-E Transparency** and **national TSO** publications—**load** and **generation** (actual and forecast where published), **outages** and **unavailability**, **cross-border** nominated capacities and flows, **imbalance** prices and volumes—subject to each operator’s **publication rules** and licences.
- **Fundamentals:** **numerical weather prediction** inputs and derived **renewables** drivers (e.g. wind speed at relevant height, **irradiance** for solar), **commodity** indices relevant to thermal margins, and **CO₂** (**EU ETS**) for power–gas–carbon bridges used by the desk.
- **Governance:** **lineage**, **versioning** for restatements, separation of **vendor/exchange data** from **internal marks** and **model outputs**.

**Analytics**

- Models for **quality control**, **nowcasting** for operations, and **feature** preparation for forecasting—fed only from **governed** datasets with **as-of** discipline for historical use.

**Visualisation**

- **Forward curves** and **spreads** (time, geography, product); **heatmaps** (e.g. tenor × zone); **volatility** views where options data exists; **drill-down** from book to trade; **depth** or **order-book** views only where **data licence** and **connectivity** allow.

---

## Trade capture and pricing

- Capture of **OTC** and **exchange-traded** exposures with correct **legal and commercial** fields: **zone or hub**, **delivery window**, **profile** (including **quarter-hourly** where used), **price formula** or **fixed** price, **counterparty**, **clearing** (**CCP** vs **bilateral**), and **collateral** context.
- **PPAs**, **capacity**, **balancing** and **system services** products where the desk trades them—each mapped to **product definitions** maintained in reference data.
- **REMIT** (reportable fields and **RRM** handoff), **EMIR** (**UTI**, **LEI**, **clearing** flags) where the entity is in scope—**data capture** and **export**; legal interpretation stays with compliance.
- **Marking** and **valuation** using **official curves** and **vol** inputs, with **audit** on overrides; **multi-commodity** structures (e.g. power–gas–CO₂) with explicit **leg** and **settlement** rules.

---

## Forecasting and predictive analytics

- **Fundamentals:** **load**, **renewable generation** (wind, solar), and optionally **thermal** availability—using **weather** and **grid** inputs actually available to the organisation (e.g. **NWP** feeds, TSO forecasts).
- **Prices and spreads** for horizons that match **market gates**: e.g. **day-ahead** auction timing, **intraday** sessions, **imbalance** settlement periods—each with **documented cut-off** and **latency** expectations.
- **Probabilistic** outputs where the desk needs **ranges** (e.g. **quantiles**, **scenarios** for renewables).
- **Evaluation:** **out-of-sample** protocols, **baselines** (naive, seasonal, vendor benchmarks), **no lookahead** in feature construction; **documentation** of known **limitations** (e.g. structural breaks, policy changes).

---

## Strategy, optimisation and algorithmic trading

- **Assisted** strategy specification and **backtesting** (parameterised rules, **documented** assumptions)—for users who are not full-time developers; **governance** over what may run in **paper** vs **production**.
- **Backtests** that include **fees**, **spreads**, **slippage**, **participation limits**, and **latency** assumptions appropriate to **SIDC** / **broker** markets—not **gross PnL** alone.
- **Optimisation** for **nominations**, **hedges**, and **dispatch** subject to **contractual** and **grid** constraints declared in scope (e.g. **storage** only if assets exist).
- **Automated** or **semi-automated** order logic where **licensed**: **pre-trade** risk checks, **limits**, **kill switches**, **monitoring**, and **reconciliation** to **fills**—consistent with **REMIT** market-abuse awareness and, where applicable, **MiFID II** algorithmic trading obligations for **investment firms**.
