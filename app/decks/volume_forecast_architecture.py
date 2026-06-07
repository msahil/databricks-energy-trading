"""Volume forecasting architecture diagram (six progressive reveal steps)."""

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
            ("cloud-sun", "NWP ensembles (ECMWF, GFS, ICON)"),
            ("thermometer", "Temperature & irradiance drivers"),
            ("gauge", "Asset SCADA & availability"),
            ("plug-zap", "AMI / industrial meter feeds"),
            ("history", "Realised generation & load actuals"),
        ),
        variant="sources",
    )
    connectivity = dip_block(
        "Lakeflow Connect",
        (
            ("hard-drive-download", "Auto Loader — weather & meters"),
            ("zap", "Structured Streaming (re-forecast loop)"),
            ("cable", "High-frequency SCADA ingest"),
            ("share-2", "Delta Share (partner weather)"),
        ),
        variant="connect",
    )
    pipelines = dip_block(
        "Lakeflow Pipelines",
        (
            ("wind", "Renewable generation ML"),
            ("users", "Zonal load & residual demand"),
            ("send", "Official publication & handoff"),
            ("activity", "Accuracy scoring & drift"),
        ),
        variant="pipelines",
    )
    models = dip_medallion_row(
        "Volume Forecast Data Models",
        (
            ("bronze", "Bronze", "NWP · SCADA · meters"),
            ("silver", "Silver", "Asset & zonal forecasts"),
            ("gold", "Gold", "Published · accuracy · alerts"),
        ),
    )
    sql_block = dip_block(
        "Analytics",
        (
            ("line-chart", "Ensemble fan & load shape"),
            ("timer", "As-of publication timeline"),
            ("bar-chart-3", "MAE / RMSE by lead time"),
        ),
        variant="sql",
    )
    ml_block = dip_block(
        "Machine Learning",
        (
            ("brain-circuit", "Wind / solar calibration"),
            ("trending-up", "Load regression per zone"),
            ("git-branch", "Champion / challenger (MLflow)"),
        ),
        variant="ml",
    )
    apps = dip_block(
        "Apps",
        (
            ("sun", "Generation forecasting desk"),
            ("zap", "Load & residual demand"),
            ("send", "Publication & handoff"),
            ("target", "Accuracy & governance"),
        ),
        variant="apps",
    )
    agents = dip_block(
        "Agents",
        (
            ("bot", "Forecast analyst copilot (planned)"),
            ("search", "Weather precedent (Vector Search)"),
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
