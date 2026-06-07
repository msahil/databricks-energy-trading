# 08 — Forecast Accuracy & Value

> Parent brief: [`main.md`](./main.md) (Capability 08). Platform and app conventions: [`instructions.md`](./instructions.md).

## Summary

Score the **published net volume** (07) and the underlying legs against what actually happened, attribute error to its source, and **translate that error into euros** of imbalance cash-out. Forecast accuracy is the module's value case: a 1% MAE improvement on a large book is worth real money, and the desk only trusts a model that proves itself. This capability computes error metrics by **lead-time bucket, leg, segment, and asset**, runs **champion / challenger** comparisons, and raises **drift alerts** when error distributions move.

It closes the loop: errors here feed back into the consumption (01/02), industrial (03), wind (05), and solar (06) models, and the **cost-of-error** view is what risk and management report on. Data is **synthetic**; the accuracy and model-governance pattern is production-shaped via MLflow + Lakehouse Monitoring.

## Databricks fit

| Capability | Role |
|---|---|
| **MLflow (registry + champion/challenger)** | Compare model variants; promote on proven accuracy |
| **Lakehouse Monitoring** | Drift detection on forecast-error distributions |
| **Delta time-travel** | Score each published vintage against realised actuals |
| **Unity Catalog** | Governed accuracy + cost tables for risk / management |

## Notebook and tables

[`../notebooks/08_forecast_accuracy_value.ipynb`](../notebooks/08_forecast_accuracy_value.ipynb) materialises:

| Layer | Tables |
|---|---|
| Gold — accuracy | `volume_forecast_gold_accuracy_daily` |
| Gold — model gov | `volume_forecast_gold_model_comparison` |
| Gold — value | `volume_forecast_gold_cost_of_error` |
| Gold — drift | `volume_forecast_gold_drift_alerts` |

Consumes published `volume_forecast_gold_net_volume` (07) + each leg's `actual_mw`. Run **last**.

**Catalog.schema:** `energy_utilities.energy_trading2`. **Grain (illustrative):** error by `leg` × `zone_code` × `lead_bucket` × `delivery_date`; lead buckets `DA`, `H+4`, `H+1`, `RT`.

---

## Accuracy & value workflow

| # | Risk / desk intent | Data / UI outcome |
|---|---|---|
| 1 | How **accurate** were we yesterday? | `volume_forecast_gold_accuracy_daily.mae_mw`, `rmse_mw`, `bias_mw` |
| 2 | **Where** did the error come from? | Error attributed by `leg` (wind / solar / consumption / industrial) |
| 3 | Does accuracy **improve with lead time**? | Metrics by `lead_bucket` (`DA` → `RT`) |
| 4 | What did error **cost** us? | `volume_forecast_gold_cost_of_error.cashout_eur` |
| 5 | Is the **challenger** better than champion? | `volume_forecast_gold_model_comparison` |
| 6 | Has the error distribution **drifted**? | `volume_forecast_gold_drift_alerts.drift_status` |

---

## Datasets

### Gold — `volume_forecast_gold_accuracy_daily`

Daily error metrics — grain `delivery_date` × `leg` × `zone_code` × `lead_bucket`.

| Column | Type | Description |
|---|---|---|
| `delivery_date` | DATE | Day scored |
| `leg` | STRING | `NET`, `CONSUMPTION`, `INDUSTRIAL`, `WIND`, `SOLAR` |
| `zone_code` | STRING | FK → zones |
| `lead_bucket` | STRING | `DA`, `H+4`, `H+1`, `RT` |
| `forecast_mw` | DOUBLE | Mean forecast (P50) |
| `actual_mw` | DOUBLE | Mean realised |
| `mae_mw` | DOUBLE | Mean absolute error |
| `rmse_mw` | DOUBLE | Root mean square error |
| `bias_mw` | DOUBLE | Signed mean error (over/under) |
| `mape_pct` | DOUBLE | Mean absolute percentage error |
| `pinball_p90` | DOUBLE | Pinball loss at P90 (band calibration) |

### Gold — `volume_forecast_gold_model_comparison`

Champion / challenger — grain `model_id` × `leg`.

| Column | Type | Description |
|---|---|---|
| `model_id` | STRING | MLflow model / run surrogate |
| `leg` | STRING | Forecast leg scored |
| `role` | STRING | `CHAMPION`, `CHALLENGER` |
| `eval_start_date` | DATE | First scored day |
| `eval_end_date` | DATE | Last scored day |
| `mae_mw` | DOUBLE | MAE over the window |
| `rmse_mw` | DOUBLE | RMSE over the window |
| `skill_score` | DOUBLE | Improvement vs naive persistence baseline |
| `is_promotion_candidate` | BOOLEAN | Challenger beats champion on the metric |

### Gold — `volume_forecast_gold_cost_of_error`

Error translated to cash-out — grain `delivery_date` × `zone_code` × `lead_bucket`.

| Column | Type | Description |
|---|---|---|
| `delivery_date` | DATE | Day |
| `zone_code` | STRING | FK → zones |
| `lead_bucket` | STRING | Lead-time bucket |
| `net_error_mw` | DOUBLE | Net volume error (signed) |
| `imbalance_price_eur_mwh` | DOUBLE | Illustrative cash-out price |
| `cashout_eur` | DOUBLE | `net_error_mw × imbalance_price` (signed cost) |
| `avoidable_eur` | DOUBLE | Cost attributable to model error vs irreducible |
| `value_at_1pct_mae_eur` | DOUBLE | € value of a 1% MAE improvement |

### Gold — `volume_forecast_gold_drift_alerts`

Drift monitoring — grain `leg` × `zone_code` × `detected_date`.

| Column | Type | Description |
|---|---|---|
| `detected_date` | DATE | When drift was flagged |
| `leg` | STRING | Forecast leg |
| `zone_code` | STRING | FK → zones |
| `metric` | STRING | `MAE`, `BIAS`, `BAND_CALIBRATION` |
| `baseline_value` | DOUBLE | Reference (training / trailing window) |
| `current_value` | DOUBLE | Current value |
| `drift_pct` | DOUBLE | Relative change |
| `drift_status` | STRING | `STABLE`, `WATCH`, `DRIFT` |

---

## App UI (Dash) — forecast accuracy & value

| Item | Value |
|---|---|
| **Route** | `/volume-forecasting/accuracy` |
| **Sidebar label** | Forecast Accuracy & Value |
| **Page module (convention)** | `app/pages/volume_forecast_accuracy.py` |
| **Data access** | `app/uc_pages.py` + `app/uc_sql.py`; header `sql-warehouse-dropdown` |

### Page layout

| Block | Content |
|---|---|
| **Hero** | Eyebrow, title, "what error costs" summary, **Presenter guide** button |
| **Toolbar** | Date range, leg, zone, lead-bucket filter |
| **Status banner** | Net MAE, bias direction, cost-of-error €, drift status |
| **Outcome cards** | MAE, RMSE, cash-out €, value of 1% MAE |
| **Error-by-leg chart** | MAE attributed by leg |
| **Lead-time curve** | Accuracy improving from DA → RT |
| **Champion/challenger panel** | Variant metrics; promotion candidate flag |
| **Cost-of-error strip** | `cashout_eur` over time; avoidable vs irreducible |
| **Drift table** | Legs in WATCH / DRIFT |
| **Presenter guide** | Problem → value case → story → who uses |

### Presenter guide (in-app modal)

| Section | Message |
|---|---|
| What problem this solves | Prove forecast quality and put a euro figure on every error |
| Why it matters | 1% MAE improvement = real cash-out avoided; models earn trust by the numbers |
| Story to tell | How accurate → where error came from → improves with lead time → what it cost → is the challenger better → is it drifting |
| Who uses this view | Risk, quant / model governance, management, desk heads |

### Widget-to-dataset binding

| UI block | Primary datasets | Key fields |
|---|---|---|
| Status banner | `volume_forecast_gold_accuracy_daily` + `cost_of_error` | `mae_mw`, `bias_mw`, `cashout_eur` |
| Error-by-leg | `volume_forecast_gold_accuracy_daily` | `leg`, `mae_mw` |
| Lead-time curve | `volume_forecast_gold_accuracy_daily` | `lead_bucket`, `mae_mw`, `rmse_mw` |
| Champion/challenger | `volume_forecast_gold_model_comparison` | `role`, `mae_mw`, `skill_score`, `is_promotion_candidate` |
| Cost-of-error strip | `volume_forecast_gold_cost_of_error` | `delivery_date`, `cashout_eur`, `avoidable_eur`, `value_at_1pct_mae_eur` |
| Drift table | `volume_forecast_gold_drift_alerts` | `leg`, `metric`, `drift_pct`, `drift_status` |

### Empty and error states

| Condition | Message / behaviour |
|---|---|
| No warehouse selected | Prompt to select a running warehouse |
| Warehouse selected, no data | Prompt to run `energy_trading_demo_data` (needs 07 first) |
| Query failure | Show error text; do not fabricate charts |

---

## Relationships

| Direction | Dependency |
|---|---|
| **Upstream** | **07** published net volume + each leg's actuals (`actual_mw` from 01, 03, 05, 06) |
| **Downstream** | Model governance feedback into 01/02/03/05/06; risk & management reporting |
| **Shared** | Consumes zones / intervals from 04 |

## Out of scope

- Real settlement / imbalance invoices (single illustrative cash-out price)
- Automated model retraining / promotion (flags candidates; promotion is a governed manual step)
- Per-trade P&L attribution (desk concern, not volume accuracy)
- In-app mock or generated series (see [`instructions.md`](./instructions.md))
