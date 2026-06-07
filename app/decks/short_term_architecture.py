"""Short-term trading architecture diagram (six progressive reveal steps)."""

from __future__ import annotations

from dash import html

from decks.architecture_diagram import (
    dip_architecture_viewport,
    dip_block,
    dip_foundation_row,
    dip_medallion_row,
    dip_segment,
)


def build_diagram() -> html.Div:
    sources = dip_block(
        "Data Sources",
        (
            ("cloud-sun", "Weather re-forecasts & satellite"),
            ("gauge", "Asset SCADA & metered output"),
            ("radio", "REMIT / outage & event feeds"),
            ("activity", "Grid frequency & balancing signals"),
            ("store", "Market gates & order-book depth"),
            ("plug-zap", "VPP submeter telemetry"),
        ),
        variant="sources",
    )
    connectivity = dip_block(
        "Lakeflow Connect",
        (
            ("hard-drive-download", "Auto Loader / streaming ingest"),
            ("zap", "Structured Streaming (Real-Time Mode)"),
            ("cable", "High-cardinality submeter feed"),
            ("share-2", "Delta Share (owner settlement)"),
        ),
        variant="connect",
    )
    pipelines = dip_block(
        "Lakeflow Pipelines",
        (
            ("line-chart", "Near-delivery squaring & imbalance"),
            ("layout-dashboard", "Control tower aggregation"),
            ("users", "DSR bid-stack & dispatch"),
        ),
        variant="pipelines",
    )
    models = dip_medallion_row(
        "Short-Term Data Models — Prompt & Spot",
        (
            ("bronze", "Bronze", "Weather · SCADA · submeters"),
            ("silver", "Silver", "Re-forecast · availability"),
            ("gold", "Gold", "Squaring · dispatch · settlement"),
        ),
    )
    sql_block = dip_block(
        "Analytics",
        (
            ("timer", "Gate countdown & squaring actions"),
            ("battery-charging", "Asset dispatch & SoC"),
            ("bar-chart-3", "DSR bid stack & settlement"),
        ),
        variant="sql",
    )
    ml_block = dip_block(
        "Machine Learning",
        (
            ("brain-circuit", "Mosaic AI dispatch policy"),
            ("trending-down", "DSR baseline & availability"),
            ("history", "Backtest replay (Delta time-travel)"),
        ),
        variant="ml",
    )
    apps = dip_block(
        "Apps",
        (
            ("layout-dashboard", "Control tower dashboard"),
            ("alert-triangle", "Near-delivery squaring desk"),
            ("network", "DSR & market access"),
        ),
        variant="apps",
    )
    agents = dip_block(
        "Agents",
        (
            ("bot", "Trading copilot (in-dash)"),
            ("search", "REMIT precedent (Vector Search)"),
        ),
        variant="agents",
    )
    foundation = dip_foundation_row(("Delta Lake", "Spark / Photon", "Unity Catalog", "MLflow"))

    return dip_architecture_viewport(
        dip_segment("1", sources),
        html.Div(
            className="dip-platform",
            children=[
                dip_segment(
                    "2",
                    html.Div("Data Intelligence Platform", className="dip-platform-banner"),
                ),
                html.Div(
                    className="dip-platform-body",
                    children=[
                        html.Div(
                            className="dip-platform-row",
                            children=[
                                html.Div(
                                    className="dip-platform-jobs-zone",
                                    children=[
                                        html.Div(
                                            className="dip-platform-jobs-row",
                                            children=[
                                                dip_segment(
                                                    "2",
                                                    html.Div(
                                                        className="dip-platform-connect",
                                                        children=[connectivity],
                                                    ),
                                                ),
                                                html.Div(
                                                    className="dip-platform-core",
                                                    children=[
                                                        html.Div(
                                                            className="dip-platform-upper",
                                                            children=[
                                                                dip_segment("3", pipelines),
                                                                dip_segment("4", ml_block),
                                                                dip_segment("5", sql_block),
                                                            ],
                                                        ),
                                                        dip_segment("3", models),
                                                        dip_segment("3", foundation),
                                                    ],
                                                ),
                                            ],
                                        ),
                                    ],
                                ),
                                dip_segment(
                                    "6",
                                    html.Div(
                                        className="dip-apps",
                                        children=[
                                            html.Div(
                                                className="dip-apps-inner",
                                                children=[apps, agents],
                                            ),
                                        ],
                                    ),
                                ),
                            ],
                        ),
                    ],
                ),
            ],
        ),
    )
