"""SQL lab — empty main content."""

import dash
from dash import html

dash.register_page(__name__, path="/sql", name="SQL lab", title="Energy Trading — SQL lab", order=9)

layout = html.Main(className="flex-1 min-h-0", children=[])
