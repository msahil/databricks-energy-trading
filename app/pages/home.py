"""Home — optional empty route at /home (app root `/` redirects to /market-data)."""

import dash
from dash import html

dash.register_page(__name__, path="/home", name="Home", title="Energy Trading — Home", order=0)

layout = html.Main(className="flex-1 min-h-0", children=[])
