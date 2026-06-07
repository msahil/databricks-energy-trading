"""Volume forecasting overview deck — slide content and configuration."""

from __future__ import annotations

from dash import html

import presentation as pres
from decks.volume_forecast_architecture import build_diagram
from slide_deck import ArchitectureOverlay, Slide, SlideDeckConfig

ARCH_STEP_TITLES: tuple[str, ...] = (
    "1) Data Sources",
    "2) Lakeflow Connect",
    "3) Volume Forecast Data Models — Lakeflow Pipelines",
    "4) Machine Learning",
    "5) Analytics · Databricks SQL",
    "6) Apps · Agents",
)

SLIDES: tuple[Slide, ...] = (
    Slide(
        "The volume forecasting desk",
        "Physical megawatts upstream of every trading decision",
        html.Div(
            className="slide-hero slide-hero-exec",
            children=[
                pres.slide_stat_row(
                    (
                        ("Day-ahead → intraday", "Rolling re-forecasts as weather updates"),
                        ("15-minute grain", "Same interval spine as prompt trading"),
                        ("Generation & load", "Wind, solar, zonal demand, residual load"),
                        ("Official as-of", "Published forecasts only reach the desk"),
                    )
                ),
                html.P(
                    "Volume forecasting answers how many megawatts the portfolio and each bidding zone will "
                    "produce and consume — before short-term traders square positions, schedulers nominate, "
                    "and long-term desks size hedges. It is physical, ensemble-driven, and accountable: "
                    "error becomes imbalance cash-out or mis-sized risk.",
                    className="slide-lead",
                ),
                pres.slide_two_col(
                    "Demand side (01–04)",
                    (
                        (
                            "Short & long term",
                            "Weather and calendar drive the next few days (01); electrification bends the multi-year shape (02).",
                        ),
                        (
                            "Industrial flexibility",
                            "A few large sites swing the zonal balance — and a slice of their load is dispatchable (03).",
                        ),
                        (
                            "Metering backbone",
                            "Millions of AMI reads become clean, private, BTM-PV-adjusted profiles every forecast reads (04).",
                        ),
                    ),
                    "Supply side & governance (05–08)",
                    (
                        (
                            "Per-asset renewables",
                            "Wind (05) and solar (06) are forecast per asset with full P10/P50/P90 ensemble spread, not zone averages.",
                        ),
                        (
                            "One official number",
                            "Demand and supply reconcile into a single published, versioned net volume — drafts never reach the desk (07).",
                        ),
                        (
                            "Accuracy in euros",
                            "MAE / RMSE / bias by lead time, drift alerts, and the cash-out cost of being wrong (08).",
                        ),
                    ),
                ),
                pres.slide_callout(
                    "Eight capabilities, one net volume",
                    "Forecast demand (01–03) on a governed metering backbone (04), forecast renewable supply per asset "
                    "(05, 06), reconcile and publish one official as-of net volume for every desk (07), and price model "
                    "accuracy with champion / challenger discipline (08).",
                    accent=True,
                ),
            ],
        ),
    ),
    Slide(
        "Where forecasting teams get stuck",
        "Ensemble complexity, publication risk, and siloed consumers",
        pres.slide_challenges_compact(
            (
                (
                    "Demand & metering",
                    "Shape, scale, privacy",
                    (
                        "Short-term weather-driven load and long-term electrification need different models on shared inputs",
                        "Millions of AMI reads arrive late, corrupt, and high-cardinality before any forecast can run",
                        "Behind-the-meter solar deduction is often missing from legacy load stacks",
                        "Household reads are personal data — consent and access control are requirements, not extras",
                    ),
                ),
                (
                    "Renewable supply",
                    "Ensemble spread",
                    (
                        "Single deterministic weather lines hide ramp risk in the hour before delivery",
                        "Wake, curtailment, and availability require asset-level calibration — not zone averages",
                        "Midday solar surplus and BTM PV must reconcile so the same kW is never counted twice",
                        "Champion models drift after new build-out without governed monitoring",
                    ),
                ),
                (
                    "Publication & value",
                    "Handoff & trust",
                    (
                        "Five forecast streams must reconcile into one official, versioned net volume",
                        "Draft runs accidentally reach nominations or squaring without an audit trail",
                        "Accuracy scoring is manual — drift is discovered after cash-out events",
                        "\u201cWe improved MAE by 2%\u201d means nothing until it is translated into euros avoided",
                    ),
                ),
            )
        ),
        body_class="slide-body slide-body-capabilities",
    ),
    Slide(
        "Capabilities · demand & metering backbone",
        "Consumption at every horizon, industrial flexibility, and the governed profile underneath them",
        pres.slide_capabilities_compact(
            (
                (
                    "Consumption · short term",
                    "Demand · near term",
                    "Forecast retail and C&I load at 15-minute grain from weather, calendar, and the curated meter profile.",
                    (
                        ("Ingest", "Weather · 04 profile"),
                        ("Model", "MLflow P10/P50/P90"),
                        ("Serve", "Demand fan to gold"),
                    ),
                    "Outcome: the demand leg the prompt desk squares against",
                ),
                (
                    "Consumption · long term",
                    "Demand · structural",
                    "Project multi-year load shapes as EVs, heat pumps, and efficiency reshape demand.",
                    (
                        ("Drivers", "EV · heat-pump · GDP"),
                        ("Simulate", "Scenario Spark runs"),
                        ("Audit", "Delta time-travel"),
                    ),
                    "Outcome: hedge-ready Cal+1…Cal+3 load shapes",
                ),
                (
                    "Industry involvement",
                    "Demand · flexible",
                    "Forecast large-site baselines and quantify the dispatchable flexibility hiding in industrial load.",
                    (
                        ("Ingest", "Site SCADA · schedules"),
                        ("Baseline", "Expected vs actual"),
                        ("Share", "Flex to DSR desk"),
                    ),
                    "Outcome: baseline plus dispatchable MW at a price",
                ),
                (
                    "Smart metering",
                    "Backbone · governed",
                    "Turn millions of AMI reads into clean, private, BTM-PV-adjusted load profiles under Unity Catalog.",
                    (
                        ("Ingest", "Auto Loader AMI"),
                        ("Curate", "DQ + BTM PV deduct"),
                        ("Govern", "UC masking · k-anon"),
                    ),
                    "Outcome: one trusted profile every forecast reads",
                ),
            )
        ),
        body_class="slide-body slide-body-capabilities",
    ),
    Slide(
        "Capabilities · supply, publication & accuracy",
        "Per-asset renewables, one official net volume, and accuracy you can price",
        pres.slide_capabilities_compact(
            (
                (
                    "Wind forecasting",
                    "Supply · volatile",
                    "Blend NWP ensembles with SCADA bias correction for per-asset wind output and its spread.",
                    (
                        ("Ingest", "NWP ensemble · SCADA"),
                        ("Model", "Power-curve MLflow"),
                        ("Serve", "P10/P50/P90 fan"),
                    ),
                    "Outcome: the largest supply leg with its uncertainty",
                ),
                (
                    "Solar forecasting",
                    "Supply · midday",
                    "Forecast utility-scale PV from irradiance and nowcasts, reconciled with behind-the-meter PV.",
                    (
                        ("Ingest", "Irradiance · nowcast"),
                        ("Model", "Irradiance → power"),
                        ("Reconcile", "BTM vs 04"),
                    ),
                    "Outcome: midday surplus without double-counting rooftop PV",
                ),
                (
                    "Publication & net volume",
                    "Govern · source of truth",
                    "Reconcile demand and supply into one official, versioned net volume with an audited handoff.",
                    (
                        ("Reconcile", "Demand − supply"),
                        ("Publish", "DRAFT → PUBLISHED"),
                        ("Handoff", "Per-consumer SLA"),
                    ),
                    "Outcome: one official net volume for every desk",
                ),
                (
                    "Forecast accuracy & value",
                    "Value · euros",
                    "Score the published cut, attribute error by leg and lead time, and translate it into cash-out euros.",
                    (
                        ("Score", "MAE · RMSE · bias"),
                        ("Cost", "Error × cash-out"),
                        ("Govern", "Champion/challenger · drift"),
                    ),
                    "Outcome: errors priced before they become cash-out",
                ),
            ),
            start_index=5,
        ),
        body_class="slide-body slide-body-capabilities",
    ),
    Slide(
        "Databricks Architecture",
        "How weather, telemetry, and meters flow through the platform to published forecasts and trading handoff",
        html.Div(),
    ),
)

CONFIG = SlideDeckConfig(
    deck_id="vf-overview",
    slides=SLIDES,
    kicker="Volume forecasting · Overview & how it fits together",
    architecture=ArchitectureOverlay(
        step_titles=ARCH_STEP_TITLES,
        build_diagram=build_diagram,
        counter_slide_number=5,
    ),
)
