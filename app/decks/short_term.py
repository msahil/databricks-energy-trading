"""Short-term trading overview deck — slide content and configuration."""

from __future__ import annotations

from dash import html

import presentation as pres
from decks.short_term_architecture import build_diagram
from slide_deck import ArchitectureOverlay, Slide, SlideDeckConfig

ARCH_STEP_TITLES: tuple[str, ...] = (
    "1) Data Sources",
    "2) Lakeflow Connect",
    "3) Short-Term Data Models — Prompt & Spot and Lakeflow Pipelines",
    "4) Machine Learning",
    "5) Analytics · Databricks SQL",
    "6) Apps · Agents",
)

SLIDES: tuple[Slide, ...] = (
    Slide(
        "The prompt & spot desk",
        "Near-delivery horizons, physical balancing, and what short-term traders optimise in real time",
        html.Div(
            className="slide-hero slide-hero-exec",
            children=[
                pres.slide_stat_row(
                    (
                        ("Week → minutes", "Week-ahead through real-time balancing"),
                        ("15-minute grain", "SDAC / XBID delivery intervals"),
                        ("Physical book", "CCGT · wind · solar · battery · DSR"),
                        ("Balancing & cash-out", "Square before the gate closes"),
                    )
                ),
                html.P(
                    "Short-term trading — the prompt and spot desk — is physical and time-critical: desks manage the "
                    "immediate reality of the grid. Traders re-forecast renewable output, square residual positions before "
                    "cross-border gate closure, co-optimise flexible assets around the clock, and aggregate third-party "
                    "flexibility into a virtual power plant.",
                    className="slide-lead",
                ),
                pres.slide_two_col(
                    "Timelines & products",
                    (
                        (
                            "Near to real time",
                            "Day-ahead and intraday auctions, XBID continuous trading, and TSO balancing (aFRR / mFRR) down to minutes before delivery.",
                        ),
                        (
                            "15-minute intervals",
                            "European markets trade and settle on quarter-hour blocks — ramp mismatches create sharp intra-hour price jumps.",
                        ),
                        (
                            "Imbalance risk",
                            "Staying long or short into delivery triggers punitive cash-out pricing from the TSO.",
                        ),
                    ),
                    "What desks focus on",
                    (
                        (
                            "Re-forecast & square",
                            "Weather updates move wind and solar forecasts; the desk must buy or sell the delta before the gate closes.",
                        ),
                        (
                            "Negative prices",
                            "Midday solar surges require batteries, DSR, or curtailment — otherwise the desk pays to stay long.",
                        ),
                        (
                            "Live dispatch",
                            "Batteries, CCGT, and aggregated flexibility must be co-optimised across intraday and balancing markets.",
                        ),
                        (
                            "Event response",
                            "REMIT outages and interconnect failures move merit order in minutes — operators need a single control-tower view.",
                        ),
                    ),
                ),
                pres.slide_callout(
                    "Three operational mandates",
                    "Square the physical delta before delivery, run the owned portfolio from a 24/7 control tower, "
                    "and monetise distributed flexibility through DSR aggregation and owner settlement.",
                    accent=True,
                ),
            ],
        ),
    ),
    Slide(
        "Where the prompt desk gets stuck",
        "Streaming latency, physical complexity, and operational fragmentation",
        pres.slide_challenges_compact(
            (
                (
                    "Near delivery",
                    "Forecast drift",
                    (
                        "Weather re-forecasts arrive continuously while gate countdowns are unforgiving",
                        "Squaring rules must be backtested before going live — research and ops share one truth",
                        "Imbalance exposure is invisible until metering diverges from nominations",
                        "Multi-stream joins across weather, SCADA, and nominations are hard in legacy stacks",
                    ),
                ),
                (
                    "Operations",
                    "Siloed consoles",
                    (
                        "Asset dispatch, grid frequency, market gates, and REMIT events live in separate tools",
                        "Operators lose minutes triaging outages while the book moves against them",
                        "Battery SoC, CCGT spark spread, and DSR availability must be read together",
                        "Shift handover depends on tribal knowledge rather than governed gold tables",
                    ),
                ),
                (
                    "DSR & VPP",
                    "Scale & settlement",
                    (
                        "Thousands of submeters create high-cardinality ingest and baseline modelling load",
                        "Prequalification rules differ per TSO product — aggregation must be auditable",
                        "Per-owner settlement requires multi-tenant governance and Delta Sharing",
                        "Negative-price absorb and evening scarcity dispatch are opposite plays on the same fleet",
                    ),
                ),
            )
        ),
        body_class="slide-body slide-body-capabilities",
    ),
    Slide(
        "How a unified platform helps",
        "Squaring, control tower, and DSR on one streaming lakehouse foundation",
        pres.slide_capabilities_compact(
            (
                (
                    "Near delivery",
                    "Square before the gate",
                    "Re-forecast renewables, quantify the residual long/short, and recommend squaring actions per interval.",
                    (
                        ("Stream", "Weather · SCADA · nominations"),
                        ("Join", "Forecast vs schedule"),
                        ("Act", "Squaring · imbalance · backtest"),
                    ),
                    "Outcome: gate countdown, cash-out exposure, and proven squaring rules",
                ),
                (
                    "Control tower",
                    "Run the physical book",
                    "One operations dashboard: balance ribbon, per-asset dispatch, grid signals, REMIT feed, and an agentic copilot.",
                    (
                        ("Aggregate", "Squaring + DSR + assets"),
                        ("Serve", "Mosaic AI dispatch policy"),
                        ("Copilot", "Draft action + rationale"),
                    ),
                    "Outcome: operator accepts the play without leaving the tower",
                ),
                (
                    "DSR & access",
                    "Virtual power plant",
                    "Ingest submeters, forecast availability, aggregate bid stacks, dispatch, and settle per owner.",
                    (
                        ("Ingest", "High-cardinality telemetry"),
                        ("Qualify", "Prequalified bid stacks"),
                        ("Share", "Owner settlement"),
                    ),
                    "Outcome: absorb at negative prices, dispatch at scarcity, settle automatically",
                ),
            )
        ),
        body_class="slide-body slide-body-capabilities",
    ),
    Slide(
        "Databricks Architecture",
        "How streaming market and asset data flows through the platform to the control tower and DSR desk",
        html.Div(),
    ),
)

CONFIG = SlideDeckConfig(
    deck_id="st-overview",
    slides=SLIDES,
    kicker="Short-term trading · Overview & how it fits together",
    architecture=ArchitectureOverlay(
        step_titles=ARCH_STEP_TITLES,
        build_diagram=build_diagram,
        counter_slide_number=4,
    ),
)
